"""Telegram notifications — optional. Token na ho to silently skip."""
import os

import requests


def send(text: str) -> bool:
    # USER DIRECTIVE (21 Sep): telegram messages OFF jab tak explicitly enable na ho
    if os.environ.get("TELEGRAM_ENABLED", "0") != "1":
        print("[notify] disabled (TELEGRAM_ENABLED=1 chahiye)")
        return False
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
