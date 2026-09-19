"""Gemini: script + topics. JSON-mode, grounded optional, validation built-in.

Fail-closed: forbidden phrases / word-count pass na ho to bounded retry (max 2),
warna RuntimeError — kabhi bhi bekaar script aage nahi jaati.
"""
import json
import os
import time

import requests

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _key() -> str:
    k = os.environ.get("GOOGLE_API_KEY", "")
    if not k:
        raise RuntimeError("GOOGLE_API_KEY missing")
    return k


def generate(model: str, prompt: str, temperature: float = 0.9,
             timeout: int = 90) -> dict:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature,
                             "responseMimeType": "application/json"},
    }
    last = None
    for attempt in range(3):
        r = requests.post(f"{BASE}/{model}:generateContent?key={_key()}",
                          json=payload, timeout=timeout)
        if r.status_code == 429:
            raise RuntimeError("GEMINI_RATE_LIMITED")
        if r.status_code >= 500:          # transient — backoff karke retry
            last = r
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    last.raise_for_status()
    raise RuntimeError("GEMINI_5XX_RETRIES_EXHAUSTED")


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
            out = generate("gemini-2.5-flash", prompt)
        except RuntimeError as e:
            if "RATE" in str(e) and attempt == 0:
                time.sleep(20)
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
        "gemini-2.5-flash-lite",
        f"Niche: {niche['display_name']}. Seed ideas: {seeds}.\n"
        f"Pehle use ho chuke topics (repeat MAT karo): {used[-30:]}\n"
        f'{n} naye, alag, specific Hindi topics ka JSON do: {{"topics":["..."]}}',
        temperature=1.0)
    return [t for t in out.get("topics", []) if t not in used][:n]
