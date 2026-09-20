"""Script Agent: WRITER + CRITIC, knowledge-base se trained.

KB = knowledge/shorts_script_kb.md — internet research se compiled rules
(hook formulas, retention pacing, phase-logic, visual-sync, critic checklist).
Writer KB ke saath beats likhta hai; Critic KB-checklist se check karke
FIXED script lauta deta hai. Har beat me: t (spoken), vis (visual desc),
phase, imp (1-3), q (search nouns).
"""
import json

from . import config, llm

KB_PATH = config.ROOT / "knowledge" / "shorts_script_kb.md"


def _kb() -> str:
    return KB_PATH.read_text(encoding="utf-8")


def write_beats(niche: dict, topic: str) -> dict:
    s = niche["script"]
    prompt = f"""{_kb()}

---
UPAR WALI KNOWLEDGE ko follow karke is topic pe SHORTS SCRIPT likho:
Topic: {topic}
Tone: {s['tone']} | Total words target: {s['word_count']}

SIRF valid JSON do:
{{"title":"40-60 chars Devanagari",
 "beats":[{{"t":"spoken Hindi line 6-10 words, grammatically poori",
            "vis":"english: concrete dikhti cheez + phase (e.g. 'hands sowing wheat seeds in soil')",
            "phase":"sowing|growth|treatment|harvest|result|general",
            "imp":2,
            "q":"2-4 english concrete nouns"}}],
 "cta":"share+subscribe line 6-12 words"}}
beats: 12 se 15. beat0=hook, beat1-2=agitation, beech=solution steps,
ek payoff, last=CTA. imp=3 sirf hook aur sabse important step ke liye."""
    return llm.generate(prompt)


CRITIC = """Tum strict YouTube Shorts CRITIC ho. Upar wali KNOWLEDGE ke
Checklist (#7) ke har point pe script check karo, jo galat ho THEEK karo,
aur poora FIXED script JSON lauto.

OUTPUT JSON:
{{"issues":["jo galat tha wo one-liner"],
 "title":"...", "cta":"...",
 "beats":[{{"t","vis","phase","imp","q"}} ...fixed...]}}
IMPORTANT: poore 12-15 beats ka POORA JSON lauto — truncate ya summary KABHI nahi.
Sab theek ho to issues=[] aur beats unchanged."""


def make_script(niche: dict, topic: str) -> dict:
    forbidden = niche["script"]["forbidden_phrases"]
    out = write_beats(niche, topic)
    for _ in range(1):
        beats = out.get("beats") or []
        narr = " ".join(b.get("t", "") for b in beats)
        if (len(beats) >= 10 and 90 <= len(narr.split()) <= 180
                and not llm.check_forbidden(narr, forbidden)):
            break
        out = write_beats(niche, topic)

    # ── CRITIC pass (KB-checklist se fix; 429-storm me ek retry) ──────────
    import time
    for attempt in range(2):
        try:
            crit = llm.generate(f"{_kb()}\n\n{CRITIC}\n\nSCRIPT JSON:\n"
                                + json.dumps(out, ensure_ascii=False))
            cb = [b for b in (crit.get("beats") or []) if str(b.get("t", "")).strip()]
            cw = len(" ".join(b["t"] for b in cb).split())
            if len(cb) >= 10 and 90 <= cw <= 180:   # critic truncated ho to writer-version rakho
                print(f"[critic] issues: {crit.get('issues', [])[:4]}")
                out["beats"] = cb
                out["title"] = crit.get("title") or out.get("title") or topic
                out["cta"] = crit.get("cta") or out.get("cta", "")
            else:
                print(f"[critic] output invalid (beats={len(cb)}, words={cw}) "
                      f"→ writer version kept")
            break
        except RuntimeError as e:
            print(f"[critic] attempt{attempt} fail: {str(e)[:60]}")
            if attempt == 0:
                time.sleep(40)

    beats = [b for b in (out.get("beats") or []) if str(b.get("t", "")).strip()]
    out["beats"] = beats
    narr = " ".join(b["t"] for b in beats)
    out["narration"] = narr
    out["words"] = len(narr.split())
    if len(beats) < 10 or not (90 <= out["words"] <= 180):
        raise RuntimeError(f"SCRIPT_INVALID beats={len(beats)} words={out['words']}")
    if llm.check_forbidden(narr, forbidden):
        raise RuntimeError("SCRIPT_FORBIDDEN_PHRASE")
    return out
