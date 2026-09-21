"""Visual Agent — Script Agent ke SEGMENT BRIEFS ka consumer (next agent).

Har brief se exact asset decision, bina andar soche:
  imp>=2 → GEN pehle (gen_prompt se AI image, 2 seeds, vision-QA) → SEARCH → card
  imp==1 → SEARCH pehle (search_q[0] → search_q[1], phase-locked, vision-QA) → GEN → card
Build karta hai synced scenes: hook-card → per-beat asset → SHARE+SUBSCRIBE card.
"""
from pathlib import Path

from . import gen, vision_qa, visuals


def _search_route(seg: dict, i: int, run):
    """search_q chain: primary → fallback; har clip phase-locked + vision-QA."""
    qs = seg.get("search_q") or [seg.get("q", "")]
    if isinstance(qs, str):
        qs = [qs]
    for j, q in enumerate(qs[:2]):
        if not str(q).strip():
            continue
        locked = visuals.locked_q({"q": q, "phase": seg.get("phase", "")}, i + j)
        clips = visuals._fetch_n(locked, run, i * 10 + j, 1)
        if clips and vision_qa.frame_matches(clips[0]["path"], seg.get("vis", ""),
                                             str(seg.get("phase", ""))):
            clips[0]["route"] = "search"
            print(f"[vagent] seg{i}: search ✅ {q}")
            return clips[0]
    return None


def _gen_route(seg: dict, i: int, run):
    """gen_prompt se exact-match AI image (2 seeds + QA). imp=3 pe i2v try."""
    prompt = seg.get("gen_prompt") or (
        f"realistic vertical 9:16 photo, {seg.get('vis', 'indian wheat field')}, "
        f"indian farm, natural daylight, no text")
    p = run / f"g{i}.jpg"
    for seed in (i * 13 + 1, i * 13 + 8):
        if gen.gen_image(prompt, p, seed) and vision_qa.frame_matches(
                p, seg.get("vis", ""), str(seg.get("phase", ""))):
            print(f"[vagent] seg{i}: gen ✅")
            return {"type": "image", "path": p, "route": "gen"}
    if p.exists():
        return {"type": "image", "path": p, "route": "gen-qa-fallback"}
    return None


def plan_segment(seg: dict, i: int, run):
    """Brief → asset dict (type/path/route) ya None (card fallback)."""
    imp = int(seg.get("imp", 1) or 1)
    order = ("gen", "search") if imp >= 2 else ("search", "gen")
    for route in order:
        asset = (_gen_route(seg, i, run) if route == "gen"
                 else _search_route(seg, i, run))
        if asset:
            return asset
    print(f"[vagent] seg{i:}: sab routes fail → card fallback")
    return None


def build_synced(niche: dict, sc: dict, run, durs: list) -> list:
    """VOICE-IMAGE SYNC: scene[i].dur == beat[i].dur.
    hook-card → per-brief planned asset (caption+overlay ke saath) → end-card."""
    run.mkdir(parents=True, exist_ok=True)
    pal = niche["visuals"]["color_palette"]
    beats = sc["beats"]
    scenes = []
    h = visuals.card(beats[0]["t"], pal, run / "card0.png", big=True)
    h["dur"] = durs[0]
    h["overlay"] = beats[0].get("overlay", "")
    scenes.append(h)
    for i, b in enumerate(beats[1:-1], start=1):
        f = plan_segment(b, i, run)
        if f is None:
            f = visuals.card(b["t"], pal, run / f"cb{i}.png")
        f["dur"] = round(durs[i], 2)
        if not f.get("static"):
            f["text"] = b["t"]
            f["overlay"] = b.get("overlay", "")
        scenes.append(f)
    cta = sc.get("cta", "") or beats[-1]["t"]
    if "शेयर" not in cta or "सब्सक्राइब" not in cta:
        cta += "\nशेयर + सब्सक्राइब"
    end = visuals.card(cta, pal, run / "cardN.png", big=True)
    end["dur"] = durs[-1]
    scenes.append(end)
    nv = sum(1 for s in scenes if s["type"] == "video")
    routes = {}
    for s in scenes:
        routes[s.get("route", "card")] = routes.get(s.get("route", "card"), 0) + 1
    print(f"[vagent] SYNCED scenes={len(scenes)} (videos={nv}) routes={routes}")
    return scenes
