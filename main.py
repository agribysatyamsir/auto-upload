"""Hindi Shorts pipeline — orchestrator.

Stages: topic → script (validated) → TTS (fail-closed) → visuals →
render (fail-closed) → upload (fail-closed) → ledger → notify.

Koi bhi stage fail = LOUD alert + exit 1. Silent success kabhi nahi.
"""
import hashlib
import json
import os
import sys
import time

from src import (config, llm, notify, render, script_agent, tts, uploader,
                 visual_agent, visuals)


def pick_music(topic: str):
    ms = sorted((config.ASSETS / "music").glob("*.mp3"))
    if not ms:
        return None
    return ms[int(hashlib.md5(topic.encode()).hexdigest(), 16) % len(ms)]


def load_plan() -> dict:
    p = config.ROOT / "content_plan.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"used_topics": [], "queue": [], "videos": []}


def save_plan(plan: dict):
    (config.ROOT / "content_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    topic = os.environ.get("TOPIC", "").strip() or None
    niche = config.load_niche()
    plan = load_plan()
    run = config.RUN
    run.mkdir(parents=True, exist_ok=True)

    if not topic:
        if plan["queue"]:
            topic = plan["queue"].pop(0)
        else:
            topic = llm.new_topics(niche, plan["used_topics"])[0]
    print(f"[topic] {topic}")
    notify.send(f"🎬 Shuru: {topic}")

    try:
        # 1) script — Writer+Critic agents, KB-trained, validated
        sc = script_agent.make_script(niche, topic)
        (run / "script.json").write_text(json.dumps(sc, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        print(f"[script] {sc['words']} words | {len(sc['beats'])} beats | hook: {sc['beats'][0]['t']}")

        # 2) TTS — fail-closed, +25% rate (natural pace)
        voices = [niche["voice"]["suggested_voices"]["edge_tts"]["hi"],
                  niche["voice"]["suggested_voices"]["edge_tts"].get("hi_fallback",
                                                                     "hi-IN-SwaraNeural")]
        # beat-wise TTS → exact durations → voice-image SYNC
        texts = [b["t"] for b in sc["beats"]]
        audio, durs = tts.synth_beats(texts, voices, run)

        # 3) visuals — per-beat matched footage (sync scenes)
        scenes = visual_agent.build_synced(niche, sc, run, durs)

        # 4) render — effects + xfade transitions + ducked BGM
        music = pick_music(topic)
        video = render.render(scenes, audio, run / "short.mp4", music=music,
                              duck=float(niche.get("music", {})
                                         .get("duck_volume_speech", 0.10)),
                              seed=topic)

        # 5) thumbnail + upload — fail-closed
        thumb = visuals.make_thumbnail(niche, sc, run)
        desc = sc["beats"][0]["t"] + " | " + niche["display_name"]
        if music:
            desc += "\n🎵 Music: Kevin MacLeod (incompetech.com), CC-BY"
        res = uploader.upload(video, sc["title"], desc,
                              thumb, privacy=config.env("PRIVACY_STATUS", "unlisted"))

        # 6) ledger + notify
        plan["used_topics"].append(topic)
        plan["videos"].append({"topic": topic, **res,
                               "ts": time.strftime("%Y-%m-%dT%H:%MZ")})
        save_plan(plan)
        notify.send(f"✅ Unlisted upload ho gaya:\n{res['url']}\nTitle: {sc['title']}")
        print("DONE", res["url"])
        return 0
    except Exception as e:
        notify.send(f"❌ PIPELINE FAIL\nTopic: {topic}\n{type(e).__name__}: {e}")
        print(f"FATAL {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
