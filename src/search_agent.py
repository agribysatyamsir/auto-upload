"""Search Agent — MULTIPLE SOURCES se footage candidates per segment-brief.

Sources (priority): Pexels videos → Pixabay videos → Pexels photos →
Pixabay photos → Archive.org. Har candidate normalized:
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
        for fn in (pexels_video_cands, pixabay_video_cands,
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
