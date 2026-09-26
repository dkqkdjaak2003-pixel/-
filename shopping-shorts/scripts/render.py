"""Render a 9:16 shopping short from jobs/<slug>/job.json.

Usage: python scripts/render.py jobs/<slug> [--font PATH]
Needs ffmpeg on PATH (or FFMPEG env var).
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

W, H, FPS = 1080, 1920, 30
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_FONTS = ["C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"]


def ffmpeg_bin():
    exe = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg를 찾을 수 없습니다. 설치하거나 FFMPEG 환경변수를 지정하세요.")
    return exe


def esc(path):
    # ffmpeg filter argument escaping for paths (Windows drive colon, backslashes)
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def wrap(text, width):
    lines = []
    for para in text.split("\n"):
        while len(para) > width:
            cut = para.rfind(" ", 0, width + 1)
            cut = cut if cut > 0 else width
            lines.append(para[:cut].strip())
            para = para[cut:].strip()
        lines.append(para)
    return "\n".join(lines)


def text_filter(tmp, name, text, font, size, y, box_alpha):
    f = Path(tmp) / f"{name}.txt"
    f.write_text(text, encoding="utf-8")
    return (f"drawtext=fontfile='{esc(font)}':textfile='{esc(f)}':fontsize={size}:fontcolor=white"
            f":line_spacing=12:x=(w-text_w)/2:y={y}:box=1:boxcolor=black@{box_alpha}:boxborderw=18")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_dir")
    ap.add_argument("--font", help="TTF/OTF with Korean glyphs")
    a = ap.parse_args()

    job_dir = Path(a.job_dir)
    job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    font = a.font or next((p for p in DEFAULT_FONTS if Path(p).exists()), None)
    if not font:
        sys.exit("한글 폰트를 찾을 수 없습니다. --font 로 지정하세요.")
    scenes = job["scenes"]
    for s in scenes:
        if not (job_dir / s["media"]).exists():
            sys.exit(f"소재 파일 없음: {s['media']}")

    out_dir = job_dir / "out"
    out_dir.mkdir(exist_ok=True)
    total = sum(float(s["duration"]) for s in scenes)

    with tempfile.TemporaryDirectory() as tmp:
        inputs, chains = [], []
        for i, s in enumerate(scenes):
            media, dur = job_dir / s["media"], float(s["duration"])
            if media.suffix.lower() in IMAGE_EXT:
                inputs += ["-loop", "1", "-t", str(dur), "-i", str(media)]
                # slow push-in so stills don't look frozen
                motion = (f",zoompan=z='min(zoom+0.0008,1.12)':d={int(dur * FPS)}"
                          f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
            else:
                inputs += ["-t", str(dur), "-i", str(media)]
                motion = ""
            chain = (f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                     f"setsar=1{motion},fps={FPS},trim=duration={dur},setpts=PTS-STARTPTS")
            if s.get("caption"):
                chain += "," + text_filter(tmp, f"cap{i}", wrap(s["caption"], 14), font, 72, "h*0.68", 0.45)
            chains.append(chain + f"[v{i}]")

        n = len(scenes)
        concat = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vc]"
        # disclosure stays on screen for the whole video
        disclosure = text_filter(tmp, "disc", wrap(job["disclosure"], 26), font, 40, "h*0.06", 0.6)
        graph = chains + [concat, f"[vc]{disclosure}[vout]"]

        audio = [(job_dir / job[key], vol)
                 for key, vol in (("voiceover", 1.0), ("bgm", float(job.get("bgm_volume", 0.15))))
                 if job.get(key)]
        a_idx = n
        a_labels = []
        for j, (path, vol) in enumerate(audio):
            inputs += ["-i", str(path)]
            graph.append(f"[{a_idx + j}:a]volume={vol},apad[a{j}]")
            a_labels.append(f"[a{j}]")
        if a_labels:
            graph.append("".join(a_labels) + f"amix=inputs={len(a_labels)}:normalize=0,atrim=duration={total}[aout]")
        else:
            inputs += ["-f", "lavfi", "-t", str(total), "-i", "anullsrc=r=44100:cl=stereo"]
            graph.append(f"[{a_idx}:a]anull[aout]")

        out = out_dir / "final.mp4"
        cmd = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", *inputs,
               "-filter_complex", ";".join(graph), "-map", "[vout]", "-map", "[aout]",
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-t", str(total), "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)

    for key in ("caption_instagram", "caption_threads"):
        if job.get(key):
            (out_dir / f"{key.split('_')[1]}.txt").write_text(job[key], encoding="utf-8")
    print(f"완료: {out} ({total:.1f}초)")


if __name__ == "__main__":
    main()
