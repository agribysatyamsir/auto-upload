#!/usr/bin/env python3
"""
get_refresh_token.py — YouTube upload ke liye refresh_token nikaalne ka ek-baari tool.

AAPKE LAPTOP PAR CHALAO (yahan nahi — browser chahiye).

    pip install google-auth google-auth-oauthlib requests
    python tools/get_refresh_token.py

Yeh script:
  1. Browser kholega → Google consent screen
  2. Aap "Allow" karoge
  3. refresh_token milega
  4. ⚠️ Check karega ki consent screen "Testing" mode par to nahi
     (Testing = token har 7 din me marta hai)
  5. token.json me save karega

Client secrets file: project root me `client_secrets.json`
"""

from __future__ import annotations

import http.server
import json
import socket
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
PORT = 8085
ROOT = Path(__file__).resolve().parent.parent
CLIENT_FILE = ROOT / "client_secrets.json"
TOKEN_FILE = ROOT / "token.json"


# ── Helpers ───────────────────────────────────────────────────────────────
def load_client() -> dict:
    if not CLIENT_FILE.exists():
        sys.exit(
            f"❌ {CLIENT_FILE} nahi mili.\n"
            "   GCP Console → Credentials → OAuth client → Download JSON,\n"
            "   aur usko project root me 'client_secrets.json' naam se rakho."
        )
    data = json.loads(CLIENT_FILE.read_text())
    inner = data.get("installed") or data.get("web")
    if not inner:
        sys.exit("❌ client_secrets.json me 'installed' ya 'web' key nahi mili — file corrupt?")
    if not inner.get("client_id") or not inner.get("client_secret"):
        sys.exit("❌ client_id ya client_secret missing hai.")
    return inner


def free_port() -> int:
    """Agar 8085 busy ho to koi free port le lo (Google installed-apps me
    loopback par koi bhi port allow karta hai)."""
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", PORT))
            return PORT
        except OSError:
            s2 = socket.socket()
            s2.bind(("127.0.0.1", 0))
            return s2.getsockname()[1]


class _Handler(http.server.BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None

    def do_GET(self):  # noqa: N802
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _Handler.code = q.get("code", [None])[0]
        _Handler.error = q.get("error", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if _Handler.error:
            msg = f"❌ Error: {_Handler.error}<br>Browser band karo, terminal dekho."
        elif _Handler.code:
            msg = "✅ Mil gaya! Browser band karo aur terminal dekho."
        else:
            msg = "⚠️ Kuch nahi mila."
        self.wfile.write(
            f"<html><body style='font-family:sans-serif;text-align:center;padding-top:60px'>"
            f"<h2>{msg}</h2></body></html>".encode()
        )

    def log_message(self, *a):  # silence
        pass


def build_auth_url(client: dict, port: int) -> str:
    """⚠️ access_type=offline + prompt=consent ZAROORI hain.
    Iske bina refresh_token milta hi nahi."""
    params = {
        "client_id": client["client_id"],
        "redirect_uri": f"http://localhost:{port}",
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",   # ← refresh token ke liye
        "prompt": "consent",        # ← warna silent-grant me refresh token nahi milta
    }
    return f'{client["auth_uri"]}?{urllib.parse.urlencode(params)}'


def exchange(code: str, client: dict, port: int) -> dict:
    """Authorization code → tokens. Raw response isliye chahiye kyunki
    `refresh_token_expires_in` sirf Testing mode me aata hai — yahi hamara detector hai."""
    r = requests.post(
        client["token_uri"],
        data={
            "code": code,
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "redirect_uri": f"http://localhost:{port}",
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if r.status_code != 200:
        sys.exit(f"❌ Token exchange fail (HTTP {r.status_code}):\n{r.text}")
    return r.json()


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    client = load_client()
    port = free_port()
    url = build_auth_url(client, port)

    print()
    print("=" * 68)
    print("  YouTube refresh_token nikaalna")
    print("=" * 68)
    print(f"  Project client : {client['client_id'][:30]}…")
    print(f"  Scope          : {SCOPE}")
    print(f"  Redirect       : http://localhost:{port}")
    print()
    print("  Browser khulega. Usme APNI Google account se login karke")
    print("  'Allow' dabao. (Agar 'unverified app' warning aaye to")
    print("  'Advanced' → 'Go to app' — yeh normal hai.)")
    print("=" * 68)
    print()

    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    webbrowser.open(url)
    print("  Browser ka wait kar raha hoon… (Ctrl+C se rok sakte ho)")
    print()

    try:
        while _Handler.code is None and _Handler.error is None:
            server.handle_request()
    except KeyboardInterrupt:
        server.shutdown()
        sys.exit("\n❌ Cancel kar diya.")

    server.shutdown()

    if _Handler.error:
        sys.exit(
            f"❌ Google ne error diya: {_Handler.error}\n"
            f"   URL: {url}\n\n"
            "   Aam wajah:\n"
            "   • 'access_denied' → consent screen Testing par hai aur aap\n"
            "     test users me nahi ho. GCP → OAuth consent screen →\n"
            "     apni email 'Test users' me add karo, ya app ko PUBLISH karo.\n"
            "   • 'redirect_uri_mismatch' → client 'Desktop app' nahi, 'Web' hai."
        )

    tokens = exchange(_Handler.code, client, port)

    refresh = tokens.get("refresh_token")
    if not refresh:
        sys.exit(
            "❌ refresh_token nahi mila.\n\n"
            "   Wajah: is client ke saath aapne pehle already permission de di thi,\n"
            "   aur Google dobara refresh_token nahi deta (sirf access_token deta hai).\n\n"
            "   FIX:\n"
            "     1. myaccount.google.com/permissions kholo\n"
            "     2. Apna app dhundo → 'Remove access'\n"
            "     3. Yeh script dobara chalao"
        )

    # ── ⚠️ CRITICAL CHECK: Testing mode detector ─────────────────────────
    expires_in = tokens.get("refresh_token_expires_in")

    TOKEN_FILE.write_text(json.dumps(
        {
            "refresh_token": refresh,
            "token_uri": client["token_uri"],
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "scope": SCOPE,
        },
        indent=2,
    ))
    TOKEN_FILE.chmod(0o600)

    print()
    print("=" * 68)
    if expires_in:
        days = int(expires_in) // 86400
        print(f"  ⚠️⚠️⚠️  WARNING — consent screen abhi 'TESTING' mode par hai")
        print()
        print(f"  Refresh token {days} DIN me expire ho jaayega.")
        print("  Pipeline roz chalega par har hafte token marega.")
        print()
        print("  FIX (yeh karna zaroori hai):")
        print("    1. console.cloud.google.com → APIs & Services → OAuth consent screen")
        print("    2. Search Console se apna domain verify karo")
        print("    3. Branding ke 3 fields bharo (logo optional hai)")
        print("    4. 'PUBLISH APP' dabao")
        print("    5. Google account → Security → Third-party apps → app REMOVE")
        print("    6. Yeh script DOBARA chalao — tab yeh warning nahi aani chahiye")
    else:
        print("  ✅ SUCCESS — Production mode confirm hua")
        print("     (`refresh_token_expires_in` response me NAHI aaya)")
        print("     Yeh token tab tak chalega jab tak aap khud revoke na karo.")
    print()
    print(f"  token.json save ho gayi → {TOKEN_FILE}")
    print("     ⚠️ ISKO PUBLIC REPO ME COMMIT MAT KARNA")
    print()
    print("  Ab is refresh_token ko Cloudflare Workers KV me daalna hai.")
    print("=" * 68)
    print()


if __name__ == "__main__":
    main()
