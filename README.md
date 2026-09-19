# Hindi Shorts Automation — Agri Learning Point

Roz 1 Hindi Short: topic → validated script → edge-tts → Ken Burns render → **unlisted upload** → (baad me) Telegram notify.

## GitHub Secrets (Settings → Secrets and variables → Actions)
- GOOGLE_API_KEY
- YOUTUBE_CLIENT_ID
- YOUTUBE_CLIENT_SECRET
- YOUTUBE_REFRESH_TOKEN
- PEXELS_API_KEY (optional — na ho to branded cards use hote hain)
- TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID (optional)

## Local run
pip install -r requirements.txt
GOOGLE_API_KEY=... python main.py   (TOPIC=... optional)

## Workflow
.github/workflows/shorts.yml — daily 12:30 IST + manual dispatch (topic input).
