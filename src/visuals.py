"""Visuals: Shorts-only (9:16) DENSE, engaging footage mix.

Trending-Shorts pattern: fast cuts (~2s/scene) → 30s video me 15+ scenes.
Order: hook card → Pexels vertical VIDEOS → Pexels photos → point cards → CTA.
Vertical-only hard filter; video files <12MB.
"""
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from . import config

MAX_VIDEO_BYTES = 12_000_000

# Pexels abstract query pe random popular footage lauta deta hai (club/dance etc).
# Isliye query ko concrete agriculture nouns tak sanitize karte hain.
AGRI_VOCAB = {"wheat", "field", "farm", "farmer", "fertilizer", "urea", "soil",
              "irrigation", "water", "spray", "sprayer", "crop", "leaf", "leaves",
              "plant", "seed", "seeds", "sowing", "harvest", "tractor", "rain",
              "grain", "pesticide", "potato", "onion", "tomato", "mustard",
              "cotton", "sugarcane", "corn", "rice", "paddy", "plants", "crops"}
SAFE_Q = ["wheat field", "farmer spraying crops", "fertilizer soil",
          "irrigation water", "green crop leaves", "wheat harvest",
          "tractor field", "seeds sowing"]


def sanitize_q(q: str, idx: int = 0) -> str:
    toks = [t for t in q.lower().replace(",", " ").split() if t in AGRI_VOCAB]
    if toks:
        return " ".join(toks[:3])
    return SAFE_Q[idx % len(SAFE_Q)]


def _get(url, **kw):
    return requests.get(url, timeout=kw.pop("timeout", 30), **kw)


def pexels_videos(queries: list, n: int = 4) -> list:
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        return []
    out = []
    for q in queries:
        try:
            r = _get("https://api.pexels.com/videos/search",
                     params={"query": q, "orientation": "portrait", "per_page": 5},
                     headers={"Authorization": key}, timeout=20)
            if not r.ok:
                continue
            for v in r.json().get("videos", []):
                files = [f for f in v.get("video_files", [])
                         if (f.get("width") or 0) <= (f.get("height") or 1)
                         and (f.get("file_size") or 0) < MAX_VIDEO_BYTES
                         and str(f.get("file_type")) == "video/mp4"]
                if not files:
                    continue
                best = min(files, key=lambda f: f.get("file_size") or 9e9)
                data = _get(best["link"]).content
                if len(data) < 50_000:
                    continue
                p = config.RUN / f"foot{len(out)}.mp4"
                p.write_bytes(data)
                out.append({"type": "video", "path": p,
                            "dur": float(v.get("duration") or 5)})
                print(f"[visuals] video: {q} ({len(data)//1024}KB)")
                if len(out) >= n:
                    return out
        except Exception as e:
            print(f"[visuals] pexels-video {q}: {e}")
    return out


def pexels_photos(queries: list, n: int = 10) -> list:
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        return []
    out = []
    for q in queries:
        try:
            r = _get("https://api.pexels.com/v1/search",
                     params={"query": q, "orientation": "portrait", "per_page": 4},
                     headers={"Authorization": key}, timeout=20)
            if not r.ok:
                continue
            for ph in r.json().get("photos", []):
                data = _get(ph["src"]["large"]).content
                if len(data) > 10_000:
                    p = config.RUN / f"photo{len(out)}.jpg"
                    p.write_bytes(data)
                    out.append({"type": "image", "path": p})
                if len(out) >= n:
                    return out
        except Exception as e:
            print(f"[visuals] photo {q}: {e}")
    return out


def archive_videos(query: str, n: int = 1) -> list:
    out = []
    try:
        r = _get("https://archive.org/advancedsearch.php",
                 params={"q": f"({query}) AND mediatype:(movies)",
                         "fl[]": "identifier", "sort[]": "-date",
                         "rows": 3, "output": "json"}, timeout=20)
        for doc in r.json().get("response", {}).get("docs", []):
            ident = doc["identifier"]
            meta = _get(f"https://archive.org/metadata/{ident}", timeout=20).json()
            mp4 = next((f["name"] for f in meta.get("files", [])
                        if f["name"].endswith(".mp4")
                        and (f.get("size") or "0").isdigit()
                        and int(f["size"]) < MAX_VIDEO_BYTES), None)
            if not mp4:
                continue
            data = _get(f"https://archive.org/download/{ident}/{mp4}").content
            if len(data) < 50_000:
                continue
            p = config.RUN / f"ia{len(out)}.mp4"
            p.write_bytes(data)
            out.append({"type": "video", "path": p, "dur": 6.0})
            if len(out) >= n:
                break
    except Exception as e:
        print(f"[visuals] archive: {e}")
    return out


# ── branded cards ──────────────────────────────────────────────────────────
def _wrap(d, text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def card(text, palette, out, big=False):
    if not text:
        text = " "
    img = Image.new("RGB", (1080, 1920), palette[0])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1080, 150], fill=palette[1])
    d.rectangle([0, 1770, 1080, 1920], fill=palette[1])
    d.rectangle([80, 1830, 400, 1860], fill=palette[3])
    fs = 116 if big else 88
    font = ImageFont.truetype(config.font(display=big), fs)
    lines = _wrap(d, text, font, 920)
    y = 960 - (len(lines) * int(fs * 1.35)) // 2
    for ln in lines[:8]:
        d.text((80, y), ln, font=font, fill="#FFF8E1")
        y += int(fs * 1.35)
    img.save(out)
    return {"type": "image", "path": out, "static": True}


def make_thumbnail(niche: dict, sc: dict, run) -> str:
    pal = niche["visuals"]["color_palette"]
    img = Image.new("RGB", (1080, 1920), pal[0])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1150, 1080, 1920], fill=pal[1])
    d.rectangle([70, 1080, 500, 1120], fill=pal[3])
    font = ImageFont.truetype(config.font(display=True), 150)
    lines = _wrap(d, " ".join(sc["title"].split()[:niche["thumbnail"]["max_words"] + 2]), font, 940)
    y = 1280
    for ln in lines[:3]:
        d.text((70, y), ln, font=font, fill=pal[3])
        y += 210
    out = run / "thumb.png"
    img.save(out)
    return str(out)


def build_scenes(niche: dict, sc: dict, run, audio_dur: float = 0) -> list:
    """Dense Shorts mix: ~2.2s/scene, min 12, max 24 scenes."""
    run.mkdir(parents=True, exist_ok=True)
    pal = niche["visuals"]["color_palette"]
    q = sc.get("keywords", [])[:3] or [sc.get("title", "farm")[:30]]
    target = int(min(24, max(12, (audio_dur or 45) / 2.2)))

    vids = pexels_videos(q, n=5) or archive_videos(q[0], n=2)
    photos = pexels_photos(q, n=12)

    scenes = [card(sc["hook"], pal, run / "card0.png", big=True)]
    pool = vids + photos
    scenes += pool

    # point cards se gap bharo agar footage kam ho
    for i, p in enumerate(sc.get("points", [])[:4]):
        if len(scenes) >= target:
            break
        scenes.insert(2 + i * 3, card(p, pal, run / f"card{i + 1}.png"))
    while len(scenes) < max(12, min(target, 12)):
        scenes.insert(len(scenes) - 1, card(sc.get("points", [""])[0], pal,
                                             run / f"pad{len(scenes)}.png"))
        break

    scenes.append(card(sc.get("cta", ""), pal, run / "cardN.png"))
    scenes = scenes[:max(target, 8)]
    nv = sum(1 for s in scenes if s["type"] == "video")
    print(f"[visuals] scenes={len(scenes)} (videos={nv}, photos="
          f"{sum(1 for s in scenes if s['type'] == 'image' and 'photo' in str(s['path']))})")
    return scenes


def fetch_one(query: str, run, idx: int):
    """Ek beat ke liye exact matched footage: video → photo → card-text."""
    vids = pexels_videos([query], n=1)
    if vids:
        vids[0]["path"] = vids[0]["path"].rename(run / f"b{idx}.mp4")
        return vids[0]
    ph = pexels_photos([query], n=1)
    if ph:
        ph[0]["path"] = ph[0]["path"].rename(run / f"b{idx}.jpg")
        return ph[0]
    return None


# PHASE-LOCK: beat ki phase ke hisaab se search query me phase-word jodo,
# taaki sowing bole to sowing dikhe — harvesting/paddy/carrot nahi.
PHASE_Q = {"sowing": "sowing seeds field", "growth": "green crop leaves",
           "treatment": "spraying fertilizer crops", "harvest": "harvesting wheat",
           "result": "full grain wheat field", "soil": "soil field",
           "general": "wheat farm"}


def locked_q(b: dict, idx: int) -> str:
    q = sanitize_q(b.get("q", ""), idx)
    return f"{q} {PHASE_Q.get(str(b.get('phase', 'general')).lower(), PHASE_Q['general'])}"


def _fetch_n(query: str, run, idx: int, k: int) -> list:
    """Ek beat ke liye k clips: videos pehle, phir photos."""
    query = sanitize_q(query, idx)
    out = pexels_videos([query], n=k)
    if len(out) < k:
        out += pexels_photos([sanitize_q(query, idx + 1)], n=k - len(out))
    for j, o in enumerate(out):
        o["path"] = o["path"].rename(run / f"b{idx}_{j}{o['path'].suffix}")
    return out[:k]

