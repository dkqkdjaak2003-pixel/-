#!/usr/bin/env python3
"""Assemble scene clips into a 9:16 short with ffmpeg.

Usage:
  assemble.py shorts/<slug>
Reads shorts/<slug>/script.json:
  {"scenes": [{"clip": "assets/s1.mp4", "caption": "...", "duration": 3}, ...],
   "voice": "assets/voice.mp3",   # optional
   "music": "assets/music.mp3",   # optional, mixed at -18 dB
   "disclosure": "쿠팡 파트너스 활동의 일환으로 수수료를 제공받습니다",
   "font": "Noto Sans KR"}      # optional; any installed Korean font
Writes shorts/<slug>/final.mp4 and captions.ass.
The disclosure line is kept at the top of the screen for the whole video.
"""
import json
import os
import shutil
import subprocess
import sys


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Caption,{font},72,&H00FFFFFF,&H00000000,&H80000000,1,1,5,0,2,60,60,420
Style: Disclosure,{font},34,&H00FFFFFF,&H00000000,&H80000000,0,3,2,0,8,40,40,90

[Events]
Format: Layer, Start, End, Style, Text
"""


def ts(sec):
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def ass_text(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


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
        run(["ffmpeg", "-y", "-i", os.path.join(root, sc["clip"]), "-t", str(dur),
             "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
             "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", out])
        parts.append(out)
        if sc.get("caption"):
            events.append(f"Dialogue: 0,{ts(t)},{ts(t + dur)},Caption,{ass_text(sc['caption'])}")
        t += dur

    if spec.get("disclosure"):
        events.append(f"Dialogue: 1,{ts(0)},{ts(t)},Disclosure,{ass_text(spec['disclosure'])}")
    ass_path = os.path.abspath(os.path.join(root, "captions.ass"))
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER.format(font=spec.get("font", "Noto Sans KR")) + "\n".join(events) + "\n")
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    silent = os.path.join(work, "silent.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])

    vf = "ass=" + ass_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    cmd = ["ffmpeg", "-y", "-i", silent]
    audio = [os.path.join(root, spec[k]) for k in ("voice", "music") if spec.get(k)]
    for a in audio:
        cmd += ["-i", a]
    graph = f"[0:v]{vf}[v]"
    if len(audio) == 2:
        graph += ";[2:a]volume=-18dB[m];[1:a][m]amix=inputs=2:duration=first[a]"
    cmd += ["-filter_complex", graph, "-map", "[v]"]
    if len(audio) == 2:
        cmd += ["-map", "[a]"]
    elif audio:
        cmd += ["-map", "1:a"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-t", str(t), os.path.join(root, "final.mp4")]
    run(cmd)
    print(f"done: {os.path.join(root, 'final.mp4')} ({t:.1f}s)")


if __name__ == "__main__":
    main()
