"""Auto Model Registry — future-proof LLM setup.

Design:
  * Koi model ID hardcode-lock nahi: har provider ka LIVE /models catalog
    padha jata hai; pattern se best available model chuna jata hai.
    (Kal koi model hat gaya → registry live list se dusra chun legi.)
  * Provider priority chain + per-provider KEY ROTATION.
  * HEALTH tracking: 429/5xx par provider ko cooldown; state/model_health.json.
  * Startup ping se us run ka working primary chun liya jata hai.
"""
import json
import os
import time

import requests

from . import config

GEM = "https://generativelanguage.googleapis.com/v1beta"
GROQ = "https://api.groq.com/openai/v1"
OR = "https://openrouter.ai/api/v1"


class RateErr(RuntimeError):
    pass


class SrvErr(RuntimeError):
    pass


def _raise(r):
    if r.status_code == 429:
        raise RateErr(f"429 {r.text[:80]}")
    if r.status_code >= 500:
        raise SrvErr(f"{r.status_code} {r.text[:80]}")
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:120]}")


# ── adapters ──────────────────────────────────────────────────────────────
def _extract_json(text: str):
    """Fences/trailing garbage tolerate karo: pehla { … aakhri }."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b > a:
        return json.loads(t[a:b + 1])
    return json.loads(t)


def gem_list(key):
    r = requests.get(f"{GEM}/models?key={key}", timeout=15)
    _raise(r)
    return [m["name"].split("/")[-1] for m in r.json().get("models", [])]


def gem_chat(key, model, prompt, jm):
    p = {"contents": [{"parts": [{"text": prompt}]}],
         "generationConfig": {"temperature": 0.9}}
    if jm:
        p["generationConfig"]["responseMimeType"] = "application/json"
    r = requests.post(f"{GEM}/models/{model}:generateContent?key={key}",
                      json=p, timeout=90)
    _raise(r)
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])


def groq_list(key):
    r = requests.get(f"{GROQ}/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
    _raise(r)
    return [m["id"] for m in r.json()["data"]]


def groq_chat(key, model, prompt, jm):
    body = {"model": model, "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]}
    if jm:
        body["response_format"] = {"type": "json_object"}
    last = None
    for _ in range(2):  # truncation/garbage par ek retry
        r = requests.post(f"{GROQ}/chat/completions",
                          headers={"Authorization": f"Bearer {key}"},
                          json=body, timeout=120)
        _raise(r)
        try:
            return _extract_json(r.json()["choices"][0]["message"]["content"])
        except Exception as e:
            last = e
    raise ValueError(f"groq json fail: {last}")


def sam_list(key):
    r = requests.get("https://api.sambanova.ai/v1/models",
                     headers={"Authorization": f"Bearer {key}"}, timeout=15)
    _raise(r)
    return [m["id"] for m in r.json()["data"]]


def sam_chat(key, model, prompt, jm):
    r = requests.post("https://api.sambanova.ai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                      timeout=90)
    _raise(r)
    return _extract_json(r.json()["choices"][0]["message"]["content"])


def or_list(key):
    r = requests.get(f"{OR}/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
    _raise(r)
    return [m["id"] for m in r.json()["data"]]


def or_pick(ids):
    free = [i for i in ids if i.endswith(":free")]
    for pat in ("70b", "llama", "qwen"):
        hit = [i for i in free if pat in i.lower()]
        if hit:
            return hit[0]
    return free[0] if free else None


def or_chat(key, model, prompt, jm):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if jm:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(f"{OR}/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json=body, timeout=90)
    _raise(r)
    return _extract_json(r.json()["choices"][0]["message"]["content"])


def mis_list(key):
    r = requests.get("https://api.mistral.ai/v1/models",
                     headers={"Authorization": f"Bearer {key}"}, timeout=15)
    _raise(r)
    return [m["id"] for m in r.json()["data"]]


def mis_chat(key, model, prompt, jm):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if jm:
        body["response_format"] = {"type": "json_object"}
    r = requests.post("https://api.mistral.ai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json=body, timeout=90)
    _raise(r)
    return _extract_json(r.json()["choices"][0]["message"]["content"])


# ── priority chain ─────────────────────────────────────────────────────────
PROVIDERS = [
    dict(name="gemini", env="GEMINI_KEYS", fallback_env="GOOGLE_API_KEY",
         list=gem_list, chat=gem_chat,
         pick=lambda ids: next((i for i in ("gemini-2.5-flash", "gemini-2.0-flash",
                                            "gemini-flash-latest") if i in ids), None)),
    dict(name="groq", env="GROQ_KEYS", list=groq_list, chat=groq_chat,
         pick=lambda ids: next((i for i in ("openai/gpt-oss-120b", "groq/compound",
                                            "openai/gpt-oss-20b") if i in ids), None)),
    dict(name="sambanova", env="SAMBANOVA_KEYS", list=sam_list, chat=sam_chat,
         pick=lambda ids: next((i for i in ids if "70B-Instruct" in i), None)),
    dict(name="openrouter", env="OPENROUTER_KEYS", list=or_list, chat=or_chat, pick=or_pick),
    dict(name="mistral", env="MISTRAL_KEYS", list=mis_list, chat=mis_chat,
         pick=lambda ids: next((i for i in ("mistral-small-latest", "mistral-medium-latest")
                                if i in ids), None)),
]

COOLDOWN_SEC = 30 * 60


class Registry:
    def __init__(self):
        config.STATE.mkdir(parents=True, exist_ok=True)
        self.hp = config.STATE / "model_health.json"
        self.health = json.loads(self.hp.read_text()) if self.hp.exists() else {}
        self._cat = {}

    def _keys(self, prov):
        ks = [k for k in os.environ.get(prov["env"], "").split(",") if k.strip()]
        if not ks and prov.get("fallback_env"):
            ks = [os.environ.get(prov["fallback_env"], "")]
        return [k for k in ks if k]

    def _cooled(self, name):
        h = self.health.get(name, {})
        return time.time() < h.get("cooldown_until", 0)

    def _mark(self, name, ok):
        h = self.health.setdefault(name, {"fails": 0, "cooldown_until": 0})
        if ok:
            h["fails"] = 0
            h["cooldown_until"] = 0
        else:
            h["fails"] = h.get("fails", 0) + 1
            if h["fails"] >= 2:
                h["cooldown_until"] = time.time() + COOLDOWN_SEC
        self.hp.write_text(json.dumps(self.health, indent=1))

    def catalog(self, prov):
        # 12h disk-cache: /models calls quota/RPM khatte hain (KEY DISCIPLINE)
        cf = config.STATE / "model_catalog.json"
        if prov["name"] not in self._cat:
            disk = {}
            if cf.exists():
                try:
                    disk = json.loads(cf.read_text())
                except Exception:
                    disk = {}
            ent = disk.get(prov["name"])
            if ent and time.time() - ent.get("ts", 0) < 12 * 3600 and ent.get("ids"):
                self._cat[prov["name"]] = ent["ids"]
                return ent["ids"]
            ids = []
            for k in self._keys(prov):
                try:
                    ids = prov["list"](k)
                    break
                except Exception:
                    continue
            self._cat[prov["name"]] = ids
            if ids:
                disk[prov["name"]] = {"ids": ids, "ts": time.time()}
                cf.write_text(json.dumps(disk))
        return self._cat[prov["name"]]

    def chat(self, prompt: str, json_mode: bool = True) -> dict:
        """Chain ghoomo: pehla successful provider jeeta."""
        errors = []
        for prov in PROVIDERS:
            name = prov["name"]
            if self._cooled(name):
                errors.append(f"{name}: cooled")
                continue
            try:
                model = prov["pick"](self.catalog(prov))
            except Exception as e:
                errors.append(f"{name}: catalog {e}")
                continue
            if not model:
                errors.append(f"{name}: no matching model live")
                continue
            keys = self._keys(prov)
            for k in keys:
                try:
                    out = prov["chat"](k, model, prompt, json_mode)
                    self._mark(name, True)
                    print(f"[models] {name}/{model} ✅")
                    return out
                except (RateErr, SrvErr) as e:
                    self._mark(name, False)
                    errors.append(f"{name}: {e}")
                    break          # is provider ki sab keys try mat karo agla provider lo
                except Exception as e:
                    errors.append(f"{name}/{model}: {e}")
                    continue
        raise RuntimeError("ALL_PROVIDERS_FAILED: " + " | ".join(errors[:8]))
