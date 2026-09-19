"""Telegram notifications — optional. Token na ho to silently skip."""
import os

import requests


def send(text: str) -> bool:
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (tok and chat):
        print("[notify] skip (telegram config nahi)")
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                          json={"chat_id": chat, "text": text[:4000]}, timeout=15)
        return r.ok
    except Exception as e:
        print("[notify] fail:", e)
        return False
