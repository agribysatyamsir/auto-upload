"""Free AI generation stack (Meta-alternative, user-approved):
  * Pollinations  — text→image, unlimited free, no auth (flux)
  * HuggingFace   — image→video free inference, best-effort (HF_TOKEN optional)
Fallback: generated image + render-level zoom/pan = motion. Exact visual match
hamesha guaranteed, kyunki image beat ki description se banti hai.
"""
import os
from pathlib import Path

import requests

POLLI = "https://image.pollinations.ai/prompt/{p}"

# image→video ke liye free HF inference candidates (jo pehle chale)
HF_I2V_MODELS = ["Wan-AI/Wan2.1-I2V-14B-480P",
                 "stabilityai/stable-video-diffusion-img2vid-xt-1-1"]


_PROBE = None


def available() -> bool:
    """Run-start probe: Pollinations down ho to poora gen-skip (time bachao)."""
    global _PROBE
    if _PROBE is None:
        try:
            r = requests.get(POLLI.format(p=requests.utils.quote("green wheat field")),
                             params={"width": 64, "height": 64, "nologo": "true",
                                     "seed": 1, "model": "turbo"}, timeout=12)
            _PROBE = r.ok and len(r.content) > 3_000
        except Exception:
            _PROBE = False
        print(f"[gen] pollinations {'✅ available' if _PROBE else '❌ down — gen skipped this run'}")
    return _PROBE


def gen_image(prompt: str, out: Path, seed: int = 7) -> bool:
    """Vertical 9:16 realistic image — beat ki vis description se."""
    if not available():
        return False
    for model in ("flux", "turbo"):
        try:
            r = requests.get(POLLI.format(p=requests.utils.quote(prompt)),
                             params={"width": 768, "height": 1344,
                                     "nologo": "true", "seed": seed,
                                     "model": model}, timeout=20)
            if r.ok and len(r.content) > 20_000:
                out.write_bytes(r.content)
                print(f"[gen] image ✅ {out.name} ({len(r.content)//1024}KB, {model})")
                return True
        except Exception:
            continue
    print("[gen] image fail (500/timeout)")
    return False


def gen_video(img: Path, out: Path) -> bool:
    """Image→video, best-effort. Na chale to caller image+zoom use karta hai."""
    tok = os.environ.get("HF_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    for m in HF_I2V_MODELS:
        try:
            r = requests.post(f"https://api-inference.huggingface.co/models/{m}",
                              headers=headers, data=img.read_bytes(), timeout=120)
            if r.ok and len(r.content) > 50_000 and not r.content.startswith(b"{"):
                out.write_bytes(r.content)
                print(f"[gen] i2v ✅ {m}")
                return True
        except Exception:
            continue
    return False
