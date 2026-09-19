"""ffmpeg render: cards/footage par Ken Burns + audio → 1080x1920 mp4.

Memory-safe design: har scene ALAG-Alag render hota hai (ek waqt me ek zoompan),
phir concat demuxer se judta hai + audio mux. 2GB RAM wale sandbox/runner par bhi safe.

NOTE: image input = single frame; zoompan d=frames usi ek frame se Ken Burns banata hai.
-loop 1 kabhi nahi (infinite frames → hang).
"""
import re
import shutil
import subprocess
from pathlib import Path

FPS = 25
# 1.5x headroom zoom ke liye; 8MP nahi (OOM risk)
PRE_W, PRE_H = 1620, 2880


def ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


def duration(path: Path) -> float:
    p = subprocess.run([ffmpeg_bin(), "-i", str(path)],
                       capture_output=True, text=True)
    m = re.search(r"Duration:\s+(\d+):(\d+):(\d+\.\d+)", p.stderr)
    if not m:
        raise RuntimeError(f"audio duration nahi mili: {path}")
    h, mi, s = map(float, m.groups())
    return h * 3600 + mi * 60 + s


def _scene(img: Path, out: Path, frames: int):
    cmd = [ffmpeg_bin(), "-y", "-i", str(img),
           "-vf", (f"scale={PRE_W}:{PRE_H}:force_original_aspect_ratio=increase,"
                   f"crop={PRE_W}:{PRE_H},"
                   f"zoompan=z='min(zoom+0.0011,1.25)':x='iw/2-(iw/zoom/2)':"
                   f"y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={FPS},setsar=1"),
           "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "veryfast", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(f"SCENE_FAIL {img.name}: {p.stderr[-400:]}")


def render(images: list, audio: Path, out: Path) -> Path:
    total = duration(audio)
    n = len(images)
    per = max(2.0, total / n)
    tmp = out.parent
    segs = []
    for i, img in enumerate(images):
        seg = tmp / f"seg{i}.mp4"
        _scene(img, seg, int(per * FPS))
        segs.append(seg)
        print(f"[render] scene {i + 1}/{n} ok")

    lst = tmp / "concat.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    cmd = [ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-i", str(audio), "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError("CONCAT_FAIL: " + p.stderr[-400:])
    for s in segs:
        s.unlink(missing_ok=True)
    lst.unlink(missing_ok=True)
    if not out.exists() or out.stat().st_size < 20000:
        raise RuntimeError("RENDER_FAIL_CLOSED: output bahut chhota/missing")
    print(f"[render] {out.name}: {out.stat().st_size} bytes, ~{total:.1f}s, {n} scenes")
    return out
