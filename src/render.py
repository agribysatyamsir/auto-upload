"""Ultra-pro Shorts render: fast cuts + Ken Burns VARIETY + crossfade
transitions + ducked BGM → 1080x1920 mp4.

Trending-Shorts pattern: har scene ~2s, zoom-in/zoom-out/pan-left/pan-right
rotate, scene-switch par 0.35s xfade, voice ke neeche ducked royalty-free BGM.
Memory-safe: scenes pehle alag-alag segments, phir xfade chain (do-do streams).
xfade fail ho to plain concat fallback (kabhi render nahi rukta).
"""
import random
import re
import shutil
import subprocess
from pathlib import Path

FPS = 25
PRE_W, PRE_H = 1620, 2880
XF = 0.35
TRANSITIONS = ["fade", "slideleft", "slideright", "smoothleft",
               "circleopen", "wipeleft", "radial", "coverleft"]
VARIANTS = ["zin", "zout", "panl", "panr"]


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


def _zoom_filter(variant: str, frames: int) -> str:
    base = (f"scale={PRE_W}:{PRE_H}:force_original_aspect_ratio=increase,"
            f"crop={PRE_W}:{PRE_H},")
    zp = {
        "zin":  "zoompan=z='min(zoom+0.0022,1.30)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "zout": "zoompan=z='if(lte(on,1),1.30,max(zoom-0.0022,1.0))':"
                "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "panl": "zoompan=z='1.20':x='(iw-iw/zoom)*min(on/{f},1)':y='ih/2-(ih/zoom/2)'",
        "panr": "zoompan=z='1.20':x='(iw-iw/zoom)*(1-min(on/{f},1))':"
                "y='ih/2-(ih/zoom/2)'",
    }[variant]
    zp = zp.replace("{f}", str(max(1, frames)))
    return base + zp + f":d={frames}:s=1080x1920:fps={FPS},setsar=1"


def _seg_image(img: Path, out: Path, frames: int, variant: str):
    cmd = [ffmpeg_bin(), "-y", "-i", str(img), "-vf", _zoom_filter(variant, frames),
           "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "veryfast", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(f"SCENE_FAIL {img.name}: {p.stderr[-300:]}")


def _seg_video(vid: Path, out: Path, want: float) -> float:
    have = duration(vid)
    d = max(1.5, min(want, have))
    cmd = [ffmpeg_bin(), "-y", "-i", str(vid), "-t", f"{d:.2f}",
           "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,"
                  "crop=1080:1920,fps=25,setsar=1",
           "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "veryfast", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(f"VIDEO_SEG_FAIL {vid.name}: {p.stderr[-300:]}")
    return d


def render(scenes: list, audio: Path, out: Path, music: Path | None = None,
           duck: float = 0.10, seed: str = "") -> Path:
    rng = random.Random(seed or "shorts")
    total = duration(audio)
    n = len(scenes)
    per = max(1.6, total / n)
    tmp = out.parent

    segs, durs = [], []
    for i, sc in enumerate(scenes):
        seg = tmp / f"seg{i}.mp4"
        if sc["type"] == "video":
            durs.append(_seg_video(Path(sc["path"]), seg, per))
        else:
            _seg_image(Path(sc["path"]), seg, int(per * FPS),
                       VARIANTS[(i + rng.randint(0, 1)) % 4])
            durs.append(per)
        segs.append(seg)
    print(f"[render] {n} segments ready (~{per:.1f}s each)")

    # ── transitions: ACCUMULATING xfade (har pass sirf 2 decoder → OOM-safe) ──
    acc, acc_dur = segs[0], durs[0]
    for i in range(1, n):
        nxt = tmp / f"xf{i}.mp4"
        t = rng.choice(TRANSITIONS)
        cmd = [ffmpeg_bin(), "-y", "-i", str(acc), "-i", str(segs[i]),
               "-filter_complex",
               f"[0:v][1:v]xfade=transition={t}:duration={XF}:"
               f"offset={max(0.1, acc_dur - XF):.2f}[v]",
               "-map", "[v]", "-c:v", "libx264", "-crf", "17",
               "-preset", "veryfast", "-pix_fmt", "yuv420p", str(nxt)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if p.returncode == 0 and nxt.exists():
            acc_dur = acc_dur + durs[i] - XF
        else:
            print(f"[render] xfade {i} fail → hard cut")
            nxt = tmp / f"xc{i}.mp4"
            # hard-cut fallback: acc + seg concat (2 inputs, copy nahi re-encode)
            lst = tmp / "cc.txt"
            lst.write_text(f"file '{acc}'\nfile '{segs[i]}'\n")
            subprocess.run([ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0",
                            "-i", str(lst), "-c:v", "libx264", "-crf", "17",
                            "-preset", "veryfast", "-pix_fmt", "yuv420p", str(nxt)],
                           capture_output=True, text=True, timeout=180)
            acc_dur += durs[i]
        if acc != segs[0]:
            acc.unlink(missing_ok=True)
        acc = nxt
    total_v = acc_dur

    # ── final mux: video (copy) + narration + ducked BGM — memory halka ──
    cmd = [ffmpeg_bin(), "-y", "-i", str(acc), "-i", str(audio)]
    if music and Path(music).exists():
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        fc_a = (f"[2:a]volume={duck},afade=t=in:d=0.8,"
                f"afade=t=out:st={max(0, total_v - 1.5)}:d=1.5[bgm];"
                f"[1:a][bgm]amix=inputs=2:duration=first:normalize=0[aout]")
        cmd += ["-filter_complex", fc_a, "-map", "0:v", "-map", "[aout]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-t", f"{total_v:.2f}", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError("MUX_FAIL: " + p.stderr[-500:])
    for s in segs + [acc]:
        if s != segs[0]:
            s.unlink(missing_ok=True)
    if not out.exists() or out.stat().st_size < 20000:
        raise RuntimeError("RENDER_FAIL_CLOSED")
    print(f"[render] {out.name}: {out.stat().st_size} bytes, {total_v:.1f}s, "
          f"{n} scenes, BGM={'✅' if music else '❌'}")
    return out
