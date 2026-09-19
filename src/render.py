"""ffmpeg render: mixed scenes (videos + cards/photos) → 1080x1920 Shorts mp4.

Memory-safe: har scene alag-alag segment banta hai (ek waqt me ek encode),
phir concat demuxer + audio mux. Videos ko trim+crop (zoompan nahi),
images ko Ken Burns zoompan. Sirf vertical output.
"""
import re
import shutil
import subprocess
from pathlib import Path

FPS = 25
PRE_W, PRE_H = 1620, 2880


def ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


def duration(path: Path) -> float:
    p = subprocess.run([ffmpeg_bin(), "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s+(\d+):(\d+):(\d+\.\d+)", p.stderr)
    if not m:
        raise RuntimeError(f"duration nahi mili: {path}")
    h, mi, s = map(float, m.groups())
    return h * 3600 + mi * 60 + s


def _seg_image(img: Path, out: Path, frames: int):
    cmd = [ffmpeg_bin(), "-y", "-i", str(img),
           "-vf", (f"scale={PRE_W}:{PRE_H}:force_original_aspect_ratio=increase,"
                   f"crop={PRE_W}:{PRE_H},zoompan=z='min(zoom+0.0011,1.25)':"
                   f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:"
                   f"s=1080x1920:fps={FPS},setsar=1"),
           "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "veryfast", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(f"SCENE_FAIL {img.name}: {p.stderr[-300:]}")


def _seg_video(vid: Path, out: Path, want: float):
    have = duration(vid)
    d = max(1.5, min(want, have))
    cmd = [ffmpeg_bin(), "-y", "-i", str(vid), "-t", f"{d:.2f}",
           "-vf", ("scale=1080:1920:force_original_aspect_ratio=increase,"
                   "crop=1080:1920,fps=25,setsar=1"),
           "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "veryfast", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(f"VIDEO_SEG_FAIL {vid.name}: {p.stderr[-300:]}")
    return d


def render(scenes: list, audio: Path, out: Path) -> Path:
    total = duration(audio)
    n = len(scenes)
    per = max(2.0, total / n)
    tmp = out.parent
    segs, made = [], 0.0
    for i, sc in enumerate(scenes):
        seg = tmp / f"seg{i}.mp4"
        if sc["type"] == "video":
            made += _seg_video(Path(sc["path"]), seg, per)
        else:
            _seg_image(Path(sc["path"]), seg, int(per * FPS))
            made += per
        segs.append(seg)
        print(f"[render] scene {i + 1}/{n} ({sc['type']}) ok")

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
        raise RuntimeError("RENDER_FAIL_CLOSED: output missing/chhota")
    print(f"[render] {out.name}: {out.stat().st_size} bytes, ~{total:.1f}s, {n} scenes")
    return out
