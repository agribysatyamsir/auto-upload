"""Hindi TTS: edge-tts (pinned >=7,<8) primary → fallback voice → Gemini TTS.

Fail-closed: empty/chhota file = failure (gTTS-style "200 OK no audio" trap se bachav).
"""
import asyncio
import base64
import os
import wave
from pathlib import Path

import requests

MIN_BYTES = 4096


async def _edge(text: str, voice: str, out: Path, rate: str):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def _gemini_tts(text: str, out: Path):
    key = os.environ.get("GOOGLE_API_KEY", "")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-preview-tts:generateContent?key={key}",
        json={"contents": [{"parts": [{"text": text}]}],
              "generationConfig": {
                  "responseModalities": ["AUDIO"],
                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}}},
        timeout=120)
    r.raise_for_status()
    pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    return out


def synth(text: str, voices: list, out: Path) -> Path:
    """Pehla kaam karne wala voice jeet gaya. Sab fail → Gemini TTS (wav).
    rate: +25% default — tez, natural; AI-slow feel khatam."""
    rate = os.environ.get("TTS_RATE", "+25%")
    for v in voices:
        try:
            asyncio.run(_edge(text, v, out, rate))
            if out.exists() and out.stat().st_size >= MIN_BYTES:
                print(f"[tts] {v} ✅ ({out.stat().st_size} bytes)")
                return out
            print(f"[tts] {v}: empty file — agla voice")
        except Exception as e:
            print(f"[tts] {v} fail: {type(e).__name__}")
    print("[tts] edge sab fail → Gemini TTS fallback")
    wav = out.with_suffix(".wav")
    _gemini_tts(text, wav)
    if wav.stat().st_size >= MIN_BYTES:
        return wav
    raise RuntimeError("TTS_FAIL_CLOSED: koi voice kaam nahi kara")
