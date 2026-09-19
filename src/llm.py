"""Gemini/multi-provider: script + topics. JSON-mode, validation built-in.

Transport ab src.models.Registry ke through — provider/model change ho
ya key mare, yahan kuch badalne ki zaroorat nahi.
"""
import time

from . import models

_reg = None


def registry() -> models.Registry:
    global _reg
    if _reg is None:
        _reg = models.Registry()
    return _reg


def generate(prompt: str, temperature_note: str = "") -> dict:
    return registry().chat(prompt, json_mode=True)


def check_forbidden(text: str, forbidden: list) -> list:
    return [f for f in forbidden if f and f in text]


def make_script(niche: dict, topic: str) -> dict:
    s = niche["script"]
    forbidden = s["forbidden_phrases"]
    hooks = " | ".join(h["template"] for h in s["hooks"])
    base = f"""Tum "{niche['display_name']}" channel ke liye Hindi YouTube Shorts likhte ho.
Topic: {topic}
Tone: {s['tone']}
Structure: opening={s['structure']['opening']} middle={s['structure']['middle']} closing={s['structure']['closing']}
Hook style (copy mat karo, samjho): {hooks}
Word limit: narration {s['word_count']} words, Devanagari Hindi.
FORBIDDEN (kabhi mat likho): {', '.join(forbidden)}
Number/dose/matra sirf tab likho jab 100% pakka ho; warna general salah do.
JSON do:
{{"title":"40-60 chars Devanagari title","hook":"pehle 2 second ki line","narration":"poori script","points":["3 on-screen card bullets, har ek 3-6 words"],"keywords":["4-6 English keywords for footage search"],"cta":"CTA line"}}"""

    prompt = base
    for attempt in range(2):
        try:
            out = generate(prompt)
        except RuntimeError as e:
            if attempt == 0:
                time.sleep(15)
                continue
            raise
        blob = (out.get("hook", "") + out.get("narration", "") + out.get("title", ""))
        bad = check_forbidden(blob, forbidden)
        words = len(out.get("narration", "").split())
        if bad:
            prompt = base + f"\n\nPICHLA OUTPUT REJECT hua. Forbidden phrases mile: {bad}. Inhe dobara MAT likho."
            continue
        if not (60 <= words <= 200):
            prompt = base + f"\n\nPICHLA OUTPUT REJECT: narration {words} words thi. {s['word_count']} words me likho."
            continue
        out["words"] = words
        return out
    raise RuntimeError("SCRIPT_VALIDATION_FAILED after bounded retries")


def new_topics(niche: dict, used: list, n: int = 5) -> list:
    seeds = ", ".join(niche.get("topic_seeds", [])[:12])
    out = generate(
        f"Niche: {niche['display_name']}. Seed ideas: {seeds}.\n"
        f"Pehle use ho chuke topics (repeat MAT karo): {used[-30:]}\n"
        f'{n} naye, alag, specific Hindi topics ka JSON do: {{"topics":["..."]}}')
    return [t for t in out.get("topics", []) if t not in used][:n]
