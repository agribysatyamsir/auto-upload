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

from . import config

FPS = 25
PRE_W, PRE_H = 1620, 2880
XF = 0.5   # longer, smoother blend (user directive: smooth transitions only)
TRANSITIONS = ["fade", "dissolve", "smoothleft", "smoothright",
               "radial", "circleopen"]   # harsh slide/wipe/cover family hata di
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
        # text-cards: halka center-zoom — text margin (80px) kabhi na kate
        "st":   "zoompan=z='min(zoom+0.0006,1.06)':x='iw/2-(iw/zoom/2)':"
                "y='ih/2-(ih/zoom/2)'",
    }[variant]
    zp = zp.replace("{f}", str(max(1, frames)))
    return base + zp + f":d={frames}:s=1080x1920:fps={FPS},setsar=1"


def caption_png(text: str, path: Path, burst: str = ""):
    """Hindi subtitle transparent PNG (drawtext ki jagah — overlay filter).
    burst = 2-4 word on-screen text pop (stat/emotion), top-center Baloo font."""
    from PIL import Image, ImageDraw, ImageFont
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if not cur or len(cur) + 1 + len(w) <= 24:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > 3:               # 3 lines max — overflow last me merge
        lines = lines[:2] + [" ".join(lines[2:])]
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(config.font(), 62)
    if lines:
        ws = [d.textlength(ln, font=font) for ln in lines]
        bw = int(max(ws)) + 60
        bh = len(lines) * 88 + 40
        x0 = (1080 - bw) // 2
        y0 = 1920 - 340 - bh
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=26,
                            fill=(0, 0, 0, 150))
        y = y0 + 20
        for ln in lines:
            w = d.textlength(ln, font=font)
            d.text(((1080 - w) / 2, y), ln, font=font, fill=(255, 248, 225, 255))
            y += 88
    if burst:
        bf = ImageFont.truetype(config.font(display=True), 74)
        bbw = int(d.textlength(burst, font=bf)) + 56
        x0 = (1080 - bbw) // 2
        d.rounded_rectangle([x0, 170, x0 + bbw, 282], radius=22,
                            fill=(255, 152, 0, 215))
        d.text(((1080 - d.textlength(burst, font=bf)) / 2, 188), burst,
               font=bf, fill=(33, 33, 33, 255))
    img.save(path)


def _seg_image(img: Path, out: Path, frames: int, variant: str, overlay: Path = None):
    if overlay:
        fc = f"[0:v]{_zoom_filter(variant, frames)}[v];[v][1:v]overlay=0:0[out]"
        cmd = [ffmpeg_bin(), "-y", "-i", str(img), "-i", str(overlay),
               "-filter_complex", fc, "-map", "[out]",
               "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-preset", "veryfast", str(out)]
    else:
        cmd = [ffmpeg_bin(), "-y", "-i", str(img), "-vf", _zoom_filter(variant, frames),
               "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-preset", "veryfast", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(f"SCENE_FAIL {img.name}: {p.stderr[-300:]}")


def _seg_video(vid: Path, out: Path, want: float, overlay: Path = None) -> float:
    have = duration(vid)
    d = max(1.5, min(want, have))
    # halka cinematic grade: saturation+contrast boost (stock footage pop)
    base = ("scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,fps=25,setsar=1,eq=saturation=1.12:contrast=1.06")
    if overlay:
        fc = f"[0:v]{base}[v];[v][1:v]overlay=0:0[out]"
        cmd = [ffmpeg_bin(), "-y", "-i", str(vid), "-i", str(overlay),
               "-t", f"{d:.2f}", "-filter_complex", fc, "-map", "[out]",
               "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-preset", "veryfast", str(out)]
    else:
        cmd = [ffmpeg_bin(), "-y", "-i", str(vid), "-t", f"{d:.2f}",
               "-vf", base,
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
        want = max(1.2, float(sc.get("dur", per)))   # beat-synced durations
        ov = None
        if sc.get("text") or sc.get("overlay"):
            ov = tmp / f"cap{i}.png"
            caption_png(sc.get("text", ""), ov, sc.get("overlay", ""))
        if sc["type"] == "video":
            durs.append(_seg_video(Path(sc["path"]), seg, want, ov))
        else:
            var = "st" if sc.get("static") else VARIANTS[(i + rng.randint(0, 1)) % 4]
            _seg_image(Path(sc["path"]), seg, int(want * FPS), var, ov)
            durs.append(want)
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

    # ── final mux: PROGRESS BAR + narration + ducked BGM + cut-whoosh SFX ──
    sfx = config.ASSETS / "sfx" / "whoosh.wav"
    bounds, cum = [], 0.0
    for i in range(1, n):
        cum += durs[i - 1]
        bounds.append(max(0.2, cum - XF * i))
    use_sfx = sfx.exists() and 1 <= len(bounds) <= 16
    has_music = bool(music) and Path(music).exists()

    def _mux(progress: bool, whoosh: bool):
        ins = [(str(acc), False), (str(audio), False)]
        if has_music:
            ins.append((str(music), True))
        n_w = 0
        if whoosh:
            ins += [(str(sfx), False)] * len(bounds)
            n_w = len(bounds)
        cmd = [ffmpeg_bin(), "-y"]
        for path, loop in ins:
            cmd += (["-stream_loop", "-1"] if loop else []) + ["-i", path]
        fc, maps = [], []
        vf = "[0:v]"
        if progress:
            vf += (f"drawbox=x=0:y=0:w='min(iw,iw*t/{total_v:.2f})':"
                   f"h=10:color=#FF9800@0.95:t=fill")
        vf += "[vout]"
        fc.append(vf)
        fc.append("[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[narr]")  # broadcast loudness
        parts = ["[narr]"]
        if has_music:
            fc.append(f"[2:a]volume={duck},afade=t=in:d=0.8,"
                      f"afade=t=out:st={max(0, total_v - 1.5)}:d=1.5[bgm]")
            parts.append("[bgm]")
        for j in range(n_w):
            ms = int(bounds[j] * 1000)
            fc.append(f"[{(3 if has_music else 2) + j}:a]volume=0.5,"
                      f"adelay={ms}|{ms}[w{j}]")
            parts.append(f"[w{j}]")
        fc.append("".join(parts) + f"amix=inputs={len(parts)}:duration=first:"
                  f"normalize=0[aout]")
        cmd += ["-filter_complex", ";".join(fc),
                "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-t", f"{total_v:.2f}", str(out)]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    p = _mux(True, use_sfx)
    if p.returncode != 0 or not out.exists():
        print(f"[render] pro-mux fail → simple mux")
        p = _mux(False, False)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError(f"MUX_FAIL {p.stderr[-300:]}")
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
