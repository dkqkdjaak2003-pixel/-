#!/usr/bin/env python3
"""Measure the style of reference shorts and keep a library of the numbers.

Run where ffmpeg, numpy (and optionally faster-whisper) exist — e.g. the Higgsfield sandbox.

  ref_analyze.py add <instagram post URL | direct .mp4 URL | local file> [--tag brand-film] [--lib refs.jsonl]
  ref_analyze.py profile [--tag brand-film] [--lib refs.jsonl]     # averages -> style targets

Measures: duration, cut times, shot length (mean/median), share of cuts on a beat grid,
tempo, onset count/types, energy per band (<150/150-1k/1-4k/4-11k Hz), loudness (LUFS),
speech segments and characters per second when narration exists.
Only numbers are stored; the reference media itself is never reused in our ads.
Instagram: public posts expose a video-only og:video file, so audio metrics are often
missing for them (they need login); pass a local screen recording to measure audio.
"""
import argparse
import html
import json
import os
import re
import statistics
import subprocess
import sys
import urllib.request

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())


def resolve(src, work):
    if os.path.exists(src):
        return src, {}
    meta = {}
    if "instagram.com" in src:
        page = os.path.join(work, "page.html")
        fetch(src, page)
        s = open(page, encoding="utf-8", errors="ignore").read()
        m = re.search(r'<meta property="og:video" content="([^"]+)', s)
        if not m:
            sys.exit("no og:video on the page (private post or login wall)")
        t = re.search(r'<meta property="og:title" content="([^"]*)', s)
        meta["title"] = html.unescape(t.group(1))[:120] if t else ""
        src = html.unescape(m.group(1))
    out = os.path.join(work, "ref.mp4")
    fetch(src, out)
    return out, meta


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stderr + subprocess.run(
        cmd, capture_output=True, text=True).stdout


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    j = json.loads(r.stdout)
    return float(j["format"]["duration"]), any(s["codec_type"] == "audio" for s in j["streams"])


def cuts(path, thr=0.28):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", f"select='gt(scene,{thr})',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [round(float(x), 2) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def beat_share(times, dur):
    """Best-fitting beat period for the cut list and the share of cuts within 60 ms of it."""
    if len(times) < 4:
        return None, None
    best = (0, None)
    for bpm in [x / 2 for x in range(120, 361)]:          # 60..180 bpm in 0.5 steps
        p = 60 / bpm
        for off in [i * p / 12 for i in range(12)]:
            hit = sum(1 for t in times if abs(((t - off) / p) - round((t - off) / p)) * p < 0.06)
            if hit > best[0]:
                best = (hit, bpm)
    return best[1], round(best[0] / len(times), 2)


def audio_metrics(path, work):
    import numpy as np
    wav = os.path.join(work, "a.wav")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", path, "-ac", "1",
                    "-ar", "22050", wav], check=True)
    import wave
    w = wave.open(wav)
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop, n = 512, 2048
    fr = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    S = np.abs(np.fft.rfft(fr, axis=1))
    f = np.fft.rfftfreq(n, 1 / sr)
    fps = sr / hop
    flux = np.maximum(0, np.diff(S, axis=0)).sum(1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    lags = np.arange(len(ac)) / fps
    m = (lags > 0.3) & (lags < 1.0)
    tempo = round(60 / lags[m][np.argmax(ac[m])], 1)
    pk = [i for i in range(1, len(flux) - 1) if flux[i] > 3 and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    kinds = {"boom": 0, "click": 0, "hit": 0}
    for i in pk:
        j = int(i / fps * sr)
        sp = np.abs(np.fft.rfft(x[j:j + n] * np.hanning(len(x[j:j + n])) if len(x[j:j + n]) == n else np.zeros(n)))
        if sp.sum() == 0:
            continue
        cen = (sp * f[:len(sp)]).sum() / sp.sum()
        low = sp[f[:len(sp)] < 150].sum() / sp.sum()
        kinds["boom" if low > 0.5 else "click" if cen > 2500 else "hit"] += 1
    e = [S[:, (f >= a) & (f < b)].mean() for a, b in ((20, 150), (150, 1000), (1000, 4000), (4000, 11000))]
    lufs = re.findall(r"I:\s+(-?[0-9.]+) LUFS", subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True).stderr)
    out = {"tempo_bpm": tempo, "onsets": len(pk), "onset_kinds": kinds,
           "bands_pct": [round(float(v / sum(e) * 100), 1) for v in e],
           "lufs": float(lufs[-1]) if lufs else None}
    try:
        from faster_whisper import WhisperModel
        segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(
            wav, language="ko", vad_filter=True)
        segs = list(segs)
        chars = sum(len(s.text.strip().replace(" ", "")) for s in segs)
        talk = sum(s.end - s.start for s in segs)
        out.update(speech_segments=len(segs), speech_share=round(talk / (len(x) / sr), 2),
                   chars_per_sec=round(chars / talk, 1) if talk else 0)
    except ImportError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("src")
    a.add_argument("--tag", default="")
    a.add_argument("--lib", default="refs.jsonl")
    p = sub.add_parser("profile")
    p.add_argument("--tag", default="")
    p.add_argument("--lib", default="refs.jsonl")
    args = ap.parse_args()

    if args.cmd == "add":
        work = "ref_work"
        os.makedirs(work, exist_ok=True)
        path, meta = resolve(args.src, work)
        dur, has_audio = probe(path)
        c = cuts(path)
        shots = [b - a for a, b in zip([0] + c, c + [dur])]
        bpm, share = beat_share(c, dur)
        rec = {"src": args.src, "tag": args.tag, **meta, "duration": round(dur, 2), "cuts": len(c),
               "cut_times": c, "shot_mean": round(statistics.mean(shots), 2),
               "shot_median": round(statistics.median(shots), 2),
               "cut_grid_bpm": bpm, "cuts_on_grid": share, "has_audio": has_audio}
        if has_audio:
            rec.update(audio_metrics(path, work))
        with open(args.lib, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(json.dumps({k: v for k, v in rec.items() if k != "cut_times"}, ensure_ascii=False))
    else:
        recs = [json.loads(l) for l in open(args.lib, encoding="utf-8") if l.strip()]
        recs = [r for r in recs if not args.tag or r.get("tag") == args.tag]
        if not recs:
            sys.exit("no records")
        avg = lambda k: round(statistics.mean(r[k] for r in recs if r.get(k) is not None), 2) \
            if any(r.get(k) is not None for r in recs) else None  # noqa: E731
        bands = [r["bands_pct"] for r in recs if r.get("bands_pct")]
        print(json.dumps({"n": len(recs), "tag": args.tag, "duration": avg("duration"),
                          "shot_mean": avg("shot_mean"), "shot_median": avg("shot_median"),
                          "cuts_on_grid": avg("cuts_on_grid"), "cut_grid_bpm": avg("cut_grid_bpm"),
                          "tempo_bpm": avg("tempo_bpm"), "lufs": avg("lufs"),
                          "chars_per_sec": avg("chars_per_sec"), "speech_share": avg("speech_share"),
                          "bands_pct": [round(statistics.mean(b[i] for b in bands), 1) for i in range(4)]
                          if bands else None}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
