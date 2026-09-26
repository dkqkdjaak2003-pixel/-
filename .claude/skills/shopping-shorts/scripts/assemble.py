#!/usr/bin/env python3
"""Assemble scene clips into a 9:16 short with ffmpeg.

Usage:
  assemble.py shorts/<slug>
Reads shorts/<slug>/script.json:
  {"scenes": [{"clip": "assets/s1.mp4", "duration": 3,
               "start": 0.5,            # optional in-point in the source clip (s)
               "speed": 1.4,            # optional playback speed (0.5 = slow motion)
               "caption": "...",        # one caption for the whole scene, or:
               "captions": [{"text": "넣고", "at": 0.1, "pop": true, "end": 1.0}],
               "big": "1"}, ...],       # optional huge centered number (CTA card)
   "voice": "assets/voice.mp3",        # optional narration
   "voice_at": 0.5,                     # optional narration start (s)
   "music": "assets/music.wav",        # optional; ducked under the narration
   "music_gain": -14,                   # optional dB, default -14
   "sfx": [{"file": "assets/sfx/tick.wav", "at": 0.0, "gain": -3}],   # optional
   "disclosure": "쿠팡 파트너스 활동의 일환으로 수수료를 제공받습니다",
   "font": "Noto Sans KR",             # optional; any installed Korean font
   "disclosure_font": "..."}           # optional; defaults to font
A scene clip may be "color:#2350FF" to render a solid background instead of a file.
In caption text, *word* is highlighted in yellow and "\\n" breaks the line.
Writes shorts/<slug>/final.mp4 (loudness-normalised to -14 LUFS) and captions.ass.
The disclosure line is kept at the top of the screen for the whole video.
"""
import json
import os
import re
import shutil
import subprocess
import sys


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Caption,{font},84,&H00FFFFFF,&H00000000,&H80000000,1,1,6,2,2,60,60,420
Style: Disclosure,{dfont},34,&H00FFFFFF,&H00000000,&H80000000,0,3,2,0,8,40,40,90
Style: BigNum,{font},560,&H003BD4FF,&H00000000,&H64000000,0,1,0,12,5,40,40,0

[Events]
Format: Layer, Start, End, Style, Text
"""
YELLOW = r"{\c&H3BD4FF&}"
WHITE = r"{\c&HFFFFFF&}"
POP = r"{\fscx135\fscy135\t(0,110,\fscx100\fscy100)}"


def ts(sec):
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def ass_text(text):
    text = text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")
    return re.sub(r"\*(.+?)\*", lambda m: YELLOW + m.group(1) + WHITE, text)


def run(cmd):
    cmd = [cmd[0], "-hide_banner", "-loglevel", "error"] + cmd[1:]
    subprocess.run(cmd, check=True)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found. Install it, or use edit list in script.json with CapCut.")
    root = sys.argv[1]
    with open(os.path.join(root, "script.json"), encoding="utf-8") as f:
        spec = json.load(f)
    work = os.path.join(root, "build")
    os.makedirs(work, exist_ok=True)

    parts, events, t = [], [], 0.0
    for i, sc in enumerate(spec["scenes"], 1):
        out = os.path.join(work, f"part{i:02}.mp4")
        dur = float(sc["duration"])
        speed = float(sc.get("speed", 1))
        if sc["clip"].startswith("color:"):
            src = ["-f", "lavfi", "-i", f"color=c=0x{sc['clip'][7:].lstrip('#')}:s=1080x1920:r=30"]
        else:
            src = ["-ss", str(sc.get("start", 0)), "-i", os.path.join(root, sc["clip"])]
        vf = (f"setpts=PTS/{speed},scale=1080:1920:force_original_aspect_ratio=increase,"
              f"crop=1080:1920,fps=30,tpad=stop_mode=clone:stop_duration={dur}")
        run(["ffmpeg", "-y", *src, "-vf", vf, "-t", str(dur),
             "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
        parts.append(out)
        caps = sc.get("captions") or ([{"text": sc["caption"], "at": 0}] if sc.get("caption") else [])
        for c in caps:
            start = t + float(c.get("at", 0))
            end = t + float(c.get("end", dur))
            events.append(f"Dialogue: 0,{ts(start)},{ts(end)},Caption,"
                          f"{POP if c.get('pop') else ''}{ass_text(c['text'])}")
        if sc.get("big"):
            events.append(f"Dialogue: 0,{ts(t)},{ts(t + dur)},BigNum,{POP}{ass_text(sc['big'])}")
        t += dur

    if spec.get("disclosure"):
        events.append(f"Dialogue: 1,{ts(0)},{ts(t)},Disclosure,{ass_text(spec['disclosure'])}")
    ass_path = os.path.abspath(os.path.join(root, "captions.ass"))
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER.format(font=spec.get("font", "Noto Sans KR"),
                                   dfont=spec.get("disclosure_font", spec.get("font", "Noto Sans KR")))
                + "\n".join(events) + "\n")
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    silent = os.path.join(work, "silent.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])

    # ---- audio: narration, ducked music, sound effects ----
    inputs, graph, mix = ["-i", silent], [], []

    def add_input(path):
        inputs.extend(["-i", os.path.join(root, path)])
        return len(inputs) // 2 - 1

    ms = lambda sec: int(float(sec) * 1000)  # noqa: E731
    voice_label = None
    if spec.get("voice"):
        k = add_input(spec["voice"])
        d = ms(spec.get("voice_at", 0))
        graph.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={d}|{d},"
                     f"volume={spec.get('voice_gain', 0)}dB,asplit=2[vo][vkey]")
        voice_label = "vo"
        mix.append("[vo]")
    if spec.get("music"):
        k = add_input(spec["music"])
        graph.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,"
                     f"volume={spec.get('music_gain', -14)}dB[mus]")
        if voice_label:
            graph.append("[mus][vkey]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=250[musd]")
            mix.append("[musd]")
        else:
            mix.append("[mus]")
    elif voice_label:
        graph.append("[vkey]anullsink")
    for j, fx in enumerate(spec.get("sfx", [])):
        k = add_input(fx["file"])
        d = ms(fx["at"])
        graph.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={d}|{d},"
                     f"volume={fx.get('gain', 0)}dB[fx{j}]")
        mix.append(f"[fx{j}]")

    vf = "ass=" + ass_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    graph.insert(0, f"[0:v]{vf}[v]")
    cmd = ["ffmpeg", "-y", *inputs]
    if mix:
        graph.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=longest,"
                     f"apad,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
        cmd += ["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-filter_complex", ";".join(graph), "-map", "[v]"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-t", str(t), os.path.join(root, "final.mp4")]
    run(cmd)
    print(f"done: {os.path.join(root, 'final.mp4')} ({t:.1f}s)")


if __name__ == "__main__":
    main()
