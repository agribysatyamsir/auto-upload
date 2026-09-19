#!/usr/bin/env python3
"""
get_token_cloudshell.py — Cloud Shell (ya kisi bhi headless jagah) ke liye manual OAuth flow.

Cloud Shell me:
  1. client_secrets.json upload karo (terminal ke ⋮ menu → Upload file)
  2. yeh script paste/chalao:  python3 get_token_cloudshell.py
  3. Print hua URL browser me kholo (wahi account jo channel ka malik hai)
  4. Allow → browser localhost par fail hoga (NORMAL) → address bar se code copy karo
  5. Code paste karo → refresh_token milega

Sirf python stdlib — koi pip install nahi.
"""
import json
import sys
import urllib.parse
import urllib.request

SCOPE = "https://www.googleapis.com/auth/youtube.upload"
REDIRECT = "http://localhost:8085"

# ── client load: file se, warna paste se ──────────────────────────────────
try:
    inner = json.load(open("client_secrets.json"))["installed"]
    print("  client_secrets.json mil gayi ✅")
except FileNotFoundError:
    print("  client_secrets.json nahi mili — values paste karo:")
    inner = {
        "client_id": input("  client_id: ").strip(),
        "client_secret": input("  client_secret: ").strip(),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

url = inner["auth_uri"] + "?" + urllib.parse.urlencode({
    "client_id": inner["client_id"],
    "redirect_uri": REDIRECT,
    "response_type": "code",
    "scope": SCOPE,
    "access_type": "offline",
    "prompt": "consent",
})

print()
print("═" * 70)
print("  STEP 1 — yeh URL browser me kholo (apni Google account me):")
print()
print(" ", url)
print()
print("  STEP 2 — 'Google hasn't verified' warning aaye to:")
print("           Advanced → Go to app → Allow")
print("  STEP 3 — browser localhost:8085 par 'site can't be reached' dikhayega")
print("           — NORMAL HAI. Address bar me jo code= ke baad likha hai")
print("           wo poora copy karo (age & ya end tak).")
print("═" * 70)
code = input("\n  code paste karo: ").strip()
if not code:
    sys.exit("  ❌ code khaali hai.")

req = urllib.request.Request(
    inner["token_uri"],
    data=urllib.parse.urlencode({
        "code": code,
        "client_id": inner["client_id"],
        "client_secret": inner["client_secret"],
        "redirect_uri": REDIRECT,
        "grant_type": "authorization_code",
    }).encode(),
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        t = json.load(r)
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"  ❌ HTTP {e.code}: {body}")
    if "access_denied" in body:
        print("\n  → App abhi TESTING par hai ya aap test users me nahi ho.")
        print("    Pehle Audience → Publish app karo, phir dobara chalao.")
    sys.exit(1)

refresh = t.get("refresh_token")
if not refresh:
    sys.exit("  ❌ refresh_token nahi mila — myaccount.google.com/permissions se app remove karke dobara chalao.")

print()
print("═" * 70)
if "refresh_token_expires_in" in t:
    print(f"  ⚠️ TESTING MODE — token {int(t['refresh_token_expires_in'])//86400} din me expire hoga!")
    print("     Audience → Publish app karo, permissions se app remove karo, dobara chalao.")
else:
    print("  ✅ PRODUCTION CONFIRM — token lambe samay tak chalega")
print()
print("  REFRESH_TOKEN (ise Workers KV / .env me daalna hai):")
print()
print(" ", refresh)
print()
print("═" * 70)
