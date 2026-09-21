"""Hindi TTS: gTTS-neural (keyless, natural) → edge-tts → Gemini TTS.

USER FEEDBACK: edge Madhur +25% robotic lagta tha. Google Translate ki
neural Hindi voice bina key ke milti hai aur kaafi natural hai.
Fail-closed: empty/chhota file = failure.
"""
import asyncio
import base64
import os
import re
import subprocess
import wave
from pathlib import Path

import requests

MIN_BYTES = 4096


def _gtts_chunks(text: str, limit: int = 170) -> list:
    parts, cur = [], ""
    for sent in re.split(r"(?<=[।.!?])\s+", text):
        while len(sent) > limit:              # lambi line → comma par todo
            cut = sent.rfind(",", 0, limit)
            cut = cut if cut > 60 else limit
            parts.append(sent[:cut + 1])
            sent = sent[cut + 1:]
        if len(cur) + len(sent) + 1 <= limit:
            cur = (cur + " " + sent).strip()
        else:
            if cur:
                parts.append(cur)
            cur = sent
    if cur:
        parts.append(cur)
    return parts or [text[:limit]]


def _gtts(text: str, out: Path) -> Path:
    """Google Translate neural Hindi TTS — no API key."""
    chunks = _gtts_chunks(text)
    files = []
    for i, ch in enumerate(chunks):
        r = requests.get("https://translate.google.com/translate_tts",
                         params={"ie": "UTF-8", "q": ch, "tl": "hi",
                                 "client": "tw-ob"},
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; "
                                  "Win64; x64) AppleWebKit/537.36"},
                         timeout=30)
        r.raise_for_status()
        if len(r.content) < 512:
            raise RuntimeError(f"gtts chunk{i} empty ({len(r.content)}B)")
        p = out.with_suffix(f".g{i}.mp3")
        p.write_bytes(r.content)
        files.append(p)
    if len(files) == 1:
        files[0].replace(out)
        return out
    from . import render
    lst = out.with_suffix(".glist.txt")
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    subprocess.run([render.ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(out)],
                   capture_output=True, timeout=120, check=True)
    for f in files:
        f.unlink(missing_ok=True)
    lst.unlink(missing_ok=True)
    return out


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
    """gTTS-neural pehle (natural, keyless) → edge voices → Gemini TTS."""
    if os.environ.get("TTS_ENGINE", "gtts") == "gtts":
        try:
            _gtts(text, out)
            if out.exists() and out.stat().st_size >= MIN_BYTES:
                print(f"[tts] gTTS-neural ✅ ({out.stat().st_size} bytes)")
                return out
        except Exception as e:
            print(f"[tts] gTTS fail ({type(e).__name__}) → edge")
    rate = os.environ.get("TTS_RATE", "+8%")   # +25% robotic tha — natural rakho
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


def synth_beats(texts: list, voices: list, run: Path):
    """Beat-wise TTS → exact per-beat durations → concat narration.
    Yehi voice-image sync ki chaabi hai: har scene ki duration = us beat
    ki audio duration, isliye visual switch hota hai jahan sentence badalta hai."""
    from . import render
    durs, files = [], []
    for i, t in enumerate(texts):
        p = run / f"beat{i}.mp3"
        synth(t, voices, p)
        durs.append(render.duration(p))
        files.append(p)
    lst = run / "beats.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    out = run / "narration.mp3"
    import subprocess
    subprocess.run([render.ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(out)],
                   capture_output=True, text=True, timeout=60)
    if not out.exists() or out.stat().st_size < MIN_BYTES:
        raise RuntimeError("TTS_CONCAT_FAIL")
    print(f"[tts] {len(texts)} beats → {out.name} ({out.stat().st_size} bytes), "
          f"durs={[round(d,1) for d in durs]}")
    return out, durs
