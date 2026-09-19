"""Visuals: Pexels (key optional) + designed cards/thumbnail (niche palette se).

Cards = template-first design: code sirf TEXT bharta hai, look hamesha branded.
"""
import os

import requests
from PIL import Image, ImageDraw, ImageFont

from . import config


def pexels(queries: list, n: int = 3) -> list:
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        return []
    urls = []
    for q in queries:
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                             params={"query": q, "per_page": 2, "orientation": "portrait"},
                             headers={"Authorization": key}, timeout=20)
            if r.ok:
                urls += [p["src"]["large"] for p in r.json().get("photos", [])[:1]]
        except Exception as e:
            print(f"[pexels] {q} fail: {e}")
        if len(urls) >= n:
            break
    imgs = []
    for i, u in enumerate(urls[:n]):
        try:
            data = requests.get(u, timeout=30).content
            if len(data) > 10000:
                p = config.RUN / f"scene{i}.jpg"
                p.write_bytes(data)
                imgs.append(p)
        except Exception as e:
            print(f"[pexels] download fail: {e}")
    return imgs


def _wrap(d: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list:
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


def card(text: str, palette: list, out, big: bool = False) -> str:
    if not text:
        text = " "
    img = Image.new("RGB", (1080, 1920), palette[0])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1080, 150], fill=palette[1])
    d.rectangle([0, 1770, 1080, 1920], fill=palette[1])
    d.rectangle([80, 1830, 400, 1860], fill=palette[3])   # accent bar
    fs = 116 if big else 88
    font = ImageFont.truetype(config.font(display=big), fs)
    lines = _wrap(d, text, font, 920)
    y = 960 - (len(lines) * int(fs * 1.35)) // 2
    for ln in lines[:8]:
        d.text((80, y), ln, font=font, fill="#FFF8E1")
        y += int(fs * 1.35)
    img.save(out)
    return str(out)


def make_cards(niche: dict, sc: dict, run) -> list:
    pal = niche["visuals"]["color_palette"]
    cards = [card(sc["hook"], pal, run / "card0.png", big=True)]
    for i, p in enumerate(sc.get("points", [])[:3]):
        cards.append(card(p, pal, run / f"card{i + 1}.png"))
    cards.append(card(sc.get("cta", ""), pal, run / "cardN.png"))
    return cards


def make_thumbnail(niche: dict, sc: dict, run) -> str:
    pal = niche["visuals"]["color_palette"]
    img = Image.new("RGB", (1080, 1920), palette := pal[0])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1080, 1920], fill=pal[0])
    d.rectangle([0, 1150, 1080, 1920], fill=pal[1])
    d.rectangle([70, 1080, 500, 1120], fill=pal[3])
    font = ImageFont.truetype(config.font(display=True), 150)
    max_w = niche["thumbnail"]["max_words"] + 2
    lines = _wrap(d, " ".join(sc["title"].split()[:max_w]), font, 940)
    y = 1280
    for ln in lines[:3]:
        d.text((70, y), ln, font=font, fill=pal[3])
        y += 210
    out = run / "thumb.png"
    img.save(out)
    return str(out)
