"""Search Agent — MULTIPLE SOURCES se footage candidates per segment-brief.

Sources (priority): GOOGLE IMAGES (user directive — exact-word match) →
Pexels videos → Pixabay videos → Pexels photos → Pixabay photos →
Archive.org. Har candidate normalized:
{source, id, type, path, dur, w, h, size, tags}
Dedup: ek run me same clip dobara nahi (USED ids).
Research: OpenMontage multi-source corpus + AutoShorts Pexels→Pixabay fallback.
"""
import os
from pathlib import Path

import requests

from . import config, visuals

MAX_VIDEO_BYTES = 12_000_000
USED: set = set()          # (source, id) — run-level dedup


def _get(url, **kw):
    return requests.get(url, timeout=kw.pop("timeout", 25), **kw)


def _save(url: str, name: str, run, min_bytes=10_000) -> Path | None:
    try:
        data = _get(url).content
        if len(data) < min_bytes:
            return None
        p = run / name
        p.write_bytes(data)
        return p
    except Exception:
        return None


# ── Pexels (existing fetchers se) ─────────────────────────────────────────
def pexels_video_cands(q: str, run, idx: int, n: int = 2) -> list:
    out = []
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        return out
    try:
        r = _get("https://api.pexels.com/videos/search",
                 params={"query": q, "orientation": "portrait", "per_page": 5},
                 headers={"Authorization": key})
        if not r.ok:
            return out
        for v in r.json().get("videos", []):
            vid = v.get("id")
            if ("pexels", vid) in USED:
                continue
            files = [f for f in v.get("video_files", [])
                     if (f.get("width") or 0) <= (f.get("height") or 1)
                     and (f.get("file_size") or 0) < MAX_VIDEO_BYTES
                     and str(f.get("file_type")) == "video/mp4"]
            if not files:
                continue
            best = min(files, key=lambda f: f.get("file_size") or 9e9)
            p = _save(best["link"], f"cand{idx}_{len(out)}.mp4", run, 50_000)
            if not p:
                continue
            USED.add(("pexels", vid))
            out.append({"source": "pexels", "id": vid, "type": "video", "path": p,
                        "dur": float(v.get("duration") or 5),
                        "w": best.get("width", 0), "h": best.get("height", 0),
                        "size": best.get("file_size", 0), "tags": ""})
            if len(out) >= n:
                break
    except Exception as e:
        print(f"[search] pexels-video: {str(e)[:60]}")
    return out


def pexels_photo_cands(q: str, run, idx: int, n: int = 2) -> list:
    out = []
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        return out
    try:
        r = _get("https://api.pexels.com/v1/search",
                 params={"query": q, "orientation": "portrait", "per_page": 5},
                 headers={"Authorization": key})
        if not r.ok:
            return out
        for ph in r.json().get("photos", []):
            pid = ph.get("id")
            if ("pexels", pid) in USED:
                continue
            p = _save(ph["src"]["large"], f"cand{idx}_{len(out)}.jpg", run)
            if not p:
                continue
            USED.add(("pexels", pid))
            out.append({"source": "pexels", "id": pid, "type": "image", "path": p,
                        "dur": 5.0, "w": ph.get("width", 0), "h": ph.get("height", 0),
                        "size": p.stat().st_size, "tags": ph.get("alt_text", "") or ""})
            if len(out) >= n:
                break
    except Exception as e:
        print(f"[search] pexels-photo: {str(e)[:60]}")
    return out


# ── Pixabay ───────────────────────────────────────────────────────────────
def pixabay_video_cands(q: str, run, idx: int, n: int = 2) -> list:
    out = []
    key = os.environ.get("PIXABAY_KEY", "")
    if not key:
        return out
    try:
        r = _get("https://pixabay.com/api/videos/",
                 params={"key": key, "q": q, "orientation": "vertical",
                         "per_page": 5})
        if not r.ok:
            return out
        for v in r.json().get("hits", []):
            vid = v.get("id")
            if ("pixabay", vid) in USED:
                continue
            vs = v.get("videos", {}) or {}
            pick = None
            for tier in ("small", "tiny", "medium"):
                f = vs.get(tier) or {}
                if f.get("url") and (f.get("width") or 0) <= (f.get("height") or 1) \
                        and (f.get("size") or 0) < MAX_VIDEO_BYTES:
                    pick = f
                    break
            if not pick:
                continue
            p = _save(pick["url"], f"cand{idx}_{len(out)}.mp4", run, 50_000)
            if not p:
                continue
            USED.add(("pixabay", vid))
            out.append({"source": "pixabay", "id": vid, "type": "video", "path": p,
                        "dur": float(v.get("duration") or 5),
                        "w": pick.get("width", 0), "h": pick.get("height", 0),
                        "size": pick.get("size", 0), "tags": v.get("tags", "") or ""})
            if len(out) >= n:
                break
    except Exception as e:
        print(f"[search] pixabay-video: {str(e)[:60]}")
    return out


def pixabay_photo_cands(q: str, run, idx: int, n: int = 2) -> list:
    out = []
    key = os.environ.get("PIXABAY_KEY", "")
    if not key:
        return out
    try:
        r = _get("https://pixabay.com/api/",
                 params={"key": key, "q": q, "orientation": "vertical",
                         "image_type": "photo", "per_page": 5})
        if not r.ok:
            return out
        for ph in r.json().get("hits", []):
            pid = ph.get("id")
            if ("pixabay", pid) in USED:
                continue
            p = _save(ph.get("webformatURL", ""), f"cand{idx}_{len(out)}.jpg", run)
            if not p:
                continue
            USED.add(("pixabay", pid))
            out.append({"source": "pixabay", "id": pid, "type": "image", "path": p,
                        "dur": 5.0, "w": ph.get("webformatWidth", 0),
                        "h": ph.get("webformatHeight", 0),
                        "size": p.stat().st_size, "tags": ph.get("tags", "") or ""})
            if len(out) >= n:
                break
    except Exception as e:
        print(f"[search] pixabay-photo: {str(e)[:60]}")
    return out


def openverse_cands(q: str, run, idx: int, n: int = 3) -> list:
    """Openverse API — FREE, no key, web-bhar se exact-word images (CC)."""
    out = []
    try:
        r = _get("https://api.openverse.org/v1/images/",
                 params={"q": q, "page_size": min(8, max(n, 4))},
                 headers={"User-Agent": "AgriLearningBot/1.0"}, timeout=25)
        if not r.ok:
            return out
        for im in r.json().get("results", []):
            u = im.get("url") or ""
            if not u:
                continue
            cid = im.get("id") or u[-40:]
            if ("openverse", cid) in USED:
                continue
            p = _save(u, f"cand{idx}_{len(out)}o.jpg", run, min_bytes=25_000)
            if not p:
                continue
            USED.add(("openverse", cid))
            out.append({"source": "openverse", "id": cid, "type": "image", "path": p,
                        "dur": 5.0, "w": im.get("width") or 0, "h": im.get("height") or 0,
                        "size": p.stat().st_size,
                        "tags": " ".join(t.get("name", "") for t in im.get("tags", [])[:8])})
            if len(out) >= n:
                break
        if out:
            print(f"[search] openverse: {len(out)} images")
    except Exception as e:
        print(f"[search] openverse: {str(e)[:60]}")
    return out


def commons_cands(q: str, run, idx: int, n: int = 3) -> list:
    """Wikimedia Commons — FREE, no key, real photos (proper UA zaroori)."""
    out = []
    try:
        r = _get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "generator": "search",
            "gsrsearch": f"filetype:bitmap {q}", "gsrnamespace": "6",
            "gsrlimit": str(max(n, 4)), "prop": "imageinfo",
            "iiprop": "url|size", "iiurlwidth": "1080", "format": "json"},
            headers={"User-Agent": "AgriLearningBot/1.0 (agri education)"},
            timeout=25)
        if not r.ok:
            return out
        pages = (r.json().get("query") or {}).get("pages") or {}
        for pg in pages.values():
            ii = (pg.get("imageinfo") or [{}])[0]
            u = ii.get("thumburl") or ii.get("url") or ""
            if not u:
                continue
            cid = pg.get("title", u[-40:])
            if ("commons", cid) in USED:
                continue
            p = _save(u, f"cand{idx}_{len(out)}c.jpg", run, min_bytes=25_000)
            if not p:
                continue
            USED.add(("commons", cid))
            out.append({"source": "commons", "id": cid, "type": "image", "path": p,
                        "dur": 5.0, "w": ii.get("width") or 0, "h": ii.get("height") or 0,
                        "size": p.stat().st_size, "tags": q})
            if len(out) >= n:
                break
        if out:
            print(f"[search] commons: {len(out)} images")
    except Exception as e:
        print(f"[search] commons: {str(e)[:60]}")
    return out


def google_image_cands(q: str, run, idx: int, n: int = 3) -> list:
    """Google Images — best-effort HTML scrape (koi API key nahi).

    User directive: Pexels/Pixabay par match na mile to Google se lao.
    Google ke result-page me images ["url",height,width] JSON-blobs me aati
    hain — wahi parse karte hain. Thumb/CDN-hosts filter.
    """
    out = []
    import re
    import hashlib
    try:
        r = _get("https://www.google.com/search",
                 params={"q": q, "tbm": "isch", "hl": "en"},
                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; "
                          "x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0 Safari/537.36"})
        if not r.ok:
            return out
        urls = re.findall(r'\["(https?://[^"\\\s]+?\.(?:jpg|jpeg|png))",(\d+),(\d+)\]',
                          r.text)
        seen = set()
        for u, hh, ww in urls:
            host = u.split("/")[2]
            if any(b in host for b in ("google", "gstatic", "ytimg", "googleapis")):
                continue
            if u in seen:
                continue
            seen.add(u)
            cid = hashlib.md5(u.encode()).hexdigest()[:12]
            if ("google", cid) in USED:
                continue
            p = _save(u, f"cand{idx}_{n - len(out)}g.jpg", run, min_bytes=30_000)
            if not p:
                continue
            USED.add(("google", cid))
            out.append({"source": "google", "id": cid, "type": "image", "path": p,
                        "dur": 5.0, "w": int(ww), "h": int(hh),
                        "size": p.stat().st_size, "tags": q})
            if len(out) >= n:
                break
        if out:
            print(f"[search] google-images: {len(out)} images")
    except Exception as e:
        print(f"[search] google-images: {str(e)[:60]}")
    return out


def archive_cands(q: str, run, idx: int, n: int = 1) -> list:
    old = visuals.archive_videos(q, n=n)
    for j, o in enumerate(old):
        o.update({"source": "archive", "id": f"ia{idx}{j}", "w": 0, "h": 0,
                  "size": o["path"].stat().st_size, "tags": ""})
    return old


def search_all(brief: dict, run, idx: int, max_cands: int = 6) -> list:
    """Brief ke search_q chain × sources → normalized candidate pool."""
    qs = brief.get("search_q") or [brief.get("q", "")]
    if isinstance(qs, str):
        qs = [qs]
    qs = [visuals.locked_q({"q": q, "phase": brief.get("phase", "")}, idx + k)
          for k, q in enumerate(qs[:2]) if str(q).strip()]
    pool, per = [], 0
    for q in qs:
        # USER RULE: WEB-SEARCH images pehle (exact-word match) → stock
        for fn in (openverse_cands, commons_cands, google_image_cands,
                   pexels_video_cands, pixabay_video_cands,
                   pexels_photo_cands, pixabay_photo_cands):
            got = fn(q, run, idx * 100 + per, 2)
            per += 1
            pool += got
            if len(pool) >= max_cands:
                return pool[:max_cands]
    if not pool:
        pool += archive_cands(qs[0] if qs else "farm", run, idx, 1)
    print(f"[search] seg{idx}: {len(pool)} candidates "
          f"({sum(1 for c in pool if c['type'] == 'video')} videos) "
          f"from {sorted({c['source'] for c in pool})}")
    return pool[:max_cands]
