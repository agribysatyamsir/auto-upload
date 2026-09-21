"""Visual Agent — Script Agent ke SEGMENT BRIEFS ka consumer (next agent).

Har brief se exact asset decision, bina andar soche:
  imp>=2 → GEN pehle (gen_prompt se AI image, 2 seeds, vision-QA) → SEARCH → card
  imp==1 → SEARCH pehle (search_q[0] → search_q[1], phase-locked, vision-QA) → GEN → card
Build karta hai synced scenes: hook-card → per-beat asset → SHARE+SUBSCRIBE card.
"""
from pathlib import Path

from . import gen, score_agent, search_agent, vision_qa, visuals


def _search_route(seg: dict, i: int, run, want_dur: float):
    """Multi-source pool → Score Agent best (ya A/B top-2)."""
    pool = search_agent.search_all(seg, run, i)
    if not pool:
        return None
    # USER RULE: pool me VIDEO nahi → pehle GEN try karo, mismatched photo nahi
    if not any(c.get("type") == "video" for c in pool):
        g = _gen_route(seg, i, run)
        if g and g.get("route") == "gen":
            return g
    picks = score_agent.pick_best(pool, seg, want_dur, two=want_dur >= 4.0)
    if not picks:
        return None
    if len(picks) == 2:
        for p_ in picks:
            p_["route"] = "search-ab"
        print(f"[vagent] seg{i}: A/B {picks[0]['source']}+{picks[1]['source']}")
        return {"ab": picks}
    picks[0]["route"] = "search"
    print(f"[vagent] seg{i}: search ✅ {picks[0]['source']} "
          f"score={score_agent.score(picks[0], seg, want_dur)}")
    return picks[0]


def _gen_route(seg: dict, i: int, run):
    """gen_prompt se exact-match AI image (2 seeds + QA)."""
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


def plan_segment(seg: dict, i: int, run, want_dur: float = 3.5):
    """Brief → asset dict | {"ab":[a,b]} | None (card fallback)."""
    imp = int(seg.get("imp", 1) or 1)
    order = ("gen", "search") if imp >= 2 else ("search", "gen")
    for route in order:
        asset = (_gen_route(seg, i, run) if route == "gen"
                 else _search_route(seg, i, run, want_dur))
        if asset:
            return asset
    print(f"[vagent] seg{i}: sab routes fail → card fallback")
    return None


def build_synced(niche: dict, sc: dict, run, durs: list) -> list:
    """VOICE-IMAGE SYNC: scene[i].dur == beat[i].dur.
    hook-card → per-brief planned asset (caption+overlay ke saath) → end-card."""
    run.mkdir(parents=True, exist_ok=True)
    pal = niche["visuals"]["color_palette"]
    beats = sc["beats"]
    scenes = []
    # HOOK: real footage se start (user: green-screen+text start boring tha).
    # search-first (imp=1) — koi LLM key nahi; fail → card fallback.
    f0 = plan_segment({**beats[0], "imp": min(1, int(beats[0].get("imp", 1) or 1))},
                      0, run, durs[0])
    if isinstance(f0, dict) and "ab" in f0:
        f0 = f0["ab"][0]
    if f0 is None:
        f0 = visuals.card(beats[0]["t"], pal, run / "card0.png", big=True)
    f0["dur"] = durs[0]
    f0["phase"] = str(beats[0].get("phase", ""))
    scenes.append(f0)
    for i, b in enumerate(beats[1:-1], start=1):
        f = plan_segment(b, i, run, durs[i])
        if isinstance(f, dict) and "ab" in f:      # A/B dual-visual split
            for k, asset in enumerate(f["ab"]):
                asset["dur"] = round(durs[i] / 2, 2)
                asset["text"] = b["t"]
                asset["overlay"] = b.get("overlay", "") if k == 0 else ""
                scenes.append(asset)
            continue
        if f is None:
            f = visuals.card(b["t"], pal, run / f"cb{i}.png")
        f["dur"] = round(durs[i], 2)
        f["phase"] = str(b.get("phase", ""))
        if not f.get("static"):
            f["text"] = b["t"]
            f["overlay"] = b.get("overlay", "")
        scenes.append(f)
    cta = sc.get("cta", "") or beats[-1]["t"]
    if "शेयर" not in cta or "सब्सक्राइब" not in cta:
        cta += "\nशेयर + सब्सक्राइब"
    end = visuals.card(cta, pal, run / "cardN.png", big=True)
    end["dur"] = durs[-1]
    end["phase"] = "cta"
    scenes.append(end)
    nv = sum(1 for s in scenes if s["type"] == "video")
    routes = {}
    for s in scenes:
        routes[s.get("route", "card")] = routes.get(s.get("route", "card"), 0) + 1
    print(f"[vagent] SYNCED scenes={len(scenes)} (videos={nv}) routes={routes}")
    return scenes
