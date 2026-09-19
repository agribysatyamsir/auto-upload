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
    formulas = " | ".join(s.get("hook_formulas", [])[:6])
    base = f"""Tum "{niche['display_name']}" ke liye viral Hindi YouTube Shorts likhte ho.
Topic: {topic}
Tone: {s['tone']}

BEAT-WISE SCRIPT likho — 12 se 15 BEATS (har beat = ek visual scene, voice-image sync):
- beat0 = HOOK (6-9 words): seedha shock/galat-fehmi/nuksaan. Formulas: {formulas}
  KABHI start mat karo: "welcome", "aaj hum", "dosto", "namaskar", "kisan bhai"
- beat1-2 = agitation: galti ka nuksaan, dard (chhote vakya)
- beat3.. = solution ke chhote concrete steps: time, matra, tarika. Har beat me SIRF ek baat
- aakhri beat = CTA: SHARE + SUBSCRIBE, value se jod kar

Rules:
- Har beat: EXACTLY 6-10 words ki ek boli jaane wali poori line (ek saans me bole)
- Beat text = sirf dialogue — keyword list/adhura vakya KABHI nahi
- Har beat grammatically POORI line ho (jaise "फसल घटती" adhura hai — aisa nahi)
- Har beat ke saath "q": 2-4 English words ka CONCRETE visual query — sirf dikhti hui
  cheez (wheat field / fertilizer / irrigation water / farmer hands / crop leaves /
  soil / tractor). Abstract words (time, mistake, profit, stage) KABHI nahi
- Total narration {s['word_count']} words
- FORBIDDEN: {', '.join(forbidden)}
- Number/dose sirf 100% pakka ho tab

JSON do:
{{"title":"40-60 chars Devanagari","beats":[{{"t":"spoken line","q":"visual query"}} x12-15],"cta":"share+subscribe line"}}"""

    prompt = base
    for attempt in range(2):
        try:
            out = generate(prompt)
        except RuntimeError:
            if attempt == 0:
                time.sleep(15)
                continue
            raise
        beats = out.get("beats") or []
        narr = " ".join(b.get("t", "") for b in beats)
        blob = narr + out.get("title", "")
        bad = check_forbidden(blob, forbidden)
        words = len(narr.split())
        if bad or len(beats) < 10 or not (90 <= words <= 180):
            prompt = base + (f"\n\nREJECT: forbidden={bad}, beats={len(beats)}, words={words}. "
                             f"12-15 beats (har beat 6-10 words), 110-150 words, clean phrases.")
            continue
        out["narration"] = narr
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
