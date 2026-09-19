"""YouTube upload: refresh_token → access_token → unlisted multipart upload.

Fail-closed: video ID na mile to RuntimeError (silent success kabhi nahi).
Thumbnail set karna best-effort (scope allow kare to).
"""
import json
import os
import uuid
from pathlib import Path

import requests


def _tokens() -> str:
    cid = os.environ.get("YOUTUBE_CLIENT_ID", "")
    csec = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    rt = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    if not (cid and csec and rt):
        # token.json fallback (local dev)
        t = json.loads((Path(__file__).resolve().parent.parent / "token.json").read_text())
        cid, csec, rt = t["client_id"], t["client_secret"], t["refresh_token"]
    r = requests.post("https://oauth2.googleapis.com/token",
                      data={"client_id": cid, "client_secret": csec,
                            "refresh_token": rt, "grant_type": "refresh_token"},
                      timeout=20)
    if r.status_code == 400 and "invalid_grant" in r.text:
        raise RuntimeError("TOKEN_DEAD: refresh_token invalid — naya consent chahiye")
    r.raise_for_status()
    return r.json()["access_token"]


def upload(video: Path, title: str, description: str, thumb: Path | None,
           privacy: str = "unlisted") -> dict:
    access = _tokens()
    meta = json.dumps({"snippet": {"title": title[:100], "description": description[:400],
                                   "tags": ["hindi", "shorts", "agriculture"],
                                   "categoryId": "27"},
                       "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}).encode()
    vid = video.read_bytes()
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Type: application/json\r\n\r\n".encode() + meta +
            f"\r\n--{b}\r\nContent-Type: video/mp4\r\n\r\n".encode() + vid +
            f"\r\n--{b}--\r\n".encode())
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status",
                      data=body,
                      headers={"Authorization": "Bearer " + access,
                               "Content-Type": f"multipart/related; boundary={b}"},
                      timeout=300)
    if r.status_code != 200:
        raise RuntimeError(f"UPLOAD_FAIL {r.status_code}: {r.text[:300]}")
    up = r.json()
    if "id" not in up:
        raise RuntimeError("UPLOAD_FAIL_CLOSED: video ID nahi mila")
    # thumbnail best-effort
    if thumb and Path(thumb).exists():
        try:
            tb = uuid.uuid4().hex
            tbody = (f"--{tb}\r\nContent-Type: image/png\r\n\r\n".encode() +
                     Path(thumb).read_bytes() + f"\r\n--{tb}--\r\n".encode())
            requests.post(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={up['id']}",
                          data=tbody,
                          headers={"Authorization": "Bearer " + access,
                                   "Content-Type": f"multipart/related; boundary={tb}"},
                          timeout=60)
        except Exception as e:
            print("[upload] thumbnail skip:", e)
    return {"id": up["id"], "privacy": up["status"]["privacyStatus"],
            "url": "https://youtube.com/shorts/" + up["id"]}
