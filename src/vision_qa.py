"""Vision QA: footage frame ko beat ki visual-desc se match karta hai ya nahi.
Provider chain: Mistral-small (vision) → Gemini flash (vision).
Mismatch → caller regenerate/search-redo. Sab mare to fail-OPEN (True).
"""
import base64
import io
import os
from pathlib import Path

import requests
from PIL import Image

GEM = "https://generativelanguage.googleapis.com/v1beta"
MISTRAL = "https://api.mistral.ai/v1"


def _first(env: str) -> str:
    return (os.environ.get(env, "").split(",") or [""])[0].strip()


def _frame(path: Path) -> Path | None:
    """Video ho to pehla frame nikalo; image ho to wahi."""
    if path.suffix.lower() in (".mp4", ".webm", ".mov"):
        import subprocess
        from . import render
        t = path.with_suffix(".qa.jpg")
        subprocess.run([render.ffmpeg_bin(), "-y", "-ss", "0.5", "-i", str(path),
                        "-frames:v", "1", "-vf", "scale=512:-2", str(t)],
                       capture_output=True, timeout=60)
        return t if t.exists() else None
    return path


def _b64_small(path: Path) -> str:
    img = Image.open(path).convert("RGB")
    img.thumbnail((512, 910))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()


def _question(vis: str, phase: str) -> str:
    return (f"Vertical farm-video frame check. Expected subject: {vis} "
            f"(phase: {phase}). If the frame plausibly shows this subject and "
            f"phase, answer YES, else NO. One word only.")


def _ask_mistral(b64: str, q: str) -> str | None:
    k = _first("MISTRAL_KEYS")
    if not k:
        return None
    r = requests.post(f"{MISTRAL}/chat/completions",
                      headers={"Authorization": f"Bearer {k}"},
                      json={"model": "mistral-small-latest",
                            "messages": [{"role": "user", "content": [
                                {"type": "text", "text": q},
                                {"type": "image_url",
                                 "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                            "max_tokens": 8, "temperature": 0},
                      timeout=60)
    if r.status_code != 200:
        return None
    return r.json()["choices"][0]["message"]["content"]


def _ask_gemini(b64: str, q: str) -> str | None:
    k = _first("GEMINI_KEYS") or _first("GOOGLE_API_KEY")
    if not k:
        return None
    r = requests.post(f"{GEM}/models/gemini-2.5-flash:generateContent?key={k}",
                      json={"contents": [{"parts": [
                          {"text": q},
                          {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}]},
                      timeout=60)
    if r.status_code != 200:
        return None
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def frame_matches(path: Path, vis: str, phase: str = "") -> bool:
    if not Path(path).exists():
        return True
    fr = _frame(Path(path))
    if fr is None:
        return True
    b64 = _b64_small(fr)
    q = _question(vis, phase)
    for name, ask in (("mistral", _ask_mistral), ("gemini", _ask_gemini)):
        try:
            txt = ask(b64, q)
        except Exception as e:
            print(f"[qa] {name}: {str(e)[:60]}")
            continue
        if txt is None:
            print(f"[qa] {name}: busy/429 — next")
            continue
        ok = "YES" in txt.upper()
        print(f"[qa] {'✅' if ok else '❌'} {Path(path).name} ({name}): {txt.strip()[:20]}")
        return ok
    return True
