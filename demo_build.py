"""Demo build — sandbox me professional short (no AI keys).
gTTS-neural voice + Google Images (manual vision-verify) + phase-aware edits.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/hindi-shorts-bot")
from src import render, tts

RUN = Path("/home/user/hindi-shorts-bot/demo_run")
RUN.mkdir(exist_ok=True)

BEATS = [
    # (phase, narration, image_query) — Shorts sweet-spot ~45s, snappy lines
    ("general", "जय हिंद दोस्तो! आज quick समझेंगे टिलेज — यानी जोताई।",
     "indian farmer standing in green crop field"),
    ("definition", "टिलेज क्या है? मिट्टी को पलटकर, बीज बोने लायक तैयार करना।",
     "tractor ploughing farm field fresh soil"),
    ("types", "First — प्राइमरी टिलेज। हल या सबसॉइलर से गहरी पहली जुताई।",
     "mouldboard plough deep ploughing tractor field"),
    ("types", "Second — सेकेंडरी टिलेज। कुल्पा और पाटा से मिट्टी भुरभुरी, समतल।",
     "disc harrow cultivator leveling field soil"),
    ("types", "और जीरो टिलेज — बिना जोते सीधे बुवाई। समय और ईंधन, दोनों बचे।",
     "no till seed drill machine sowing field"),
    ("benefits", "फायदे? खरपतवार खत्म, नमी बरकरार, और जड़ें मजबूत।",
     "healthy green crop roots dark moist soil"),
    ("limitations", "पर याद रखो — ज्यादा जुताई से मिट्टी कटती है, नमी उड़ती है।",
     "soil erosion dry cracked field water runoff"),
    ("exam", "Exam one-liner — टिलेज यानी seedbed, weed control और moisture conservation।",
     "student writing agriculture exam notes notebook"),
    ("cta", "फॉलो करें Agri Learning Point — share करो, subscribe जरूर करो।",
     "youtube subscribe bell icon red button"),
]

def dur_of(p: Path) -> float:
    r = subprocess.run([render.ffmpeg_bin(), "-i", str(p)], capture_output=True, text=True)
    for ln in r.stderr.splitlines():
        if "Duration" in ln:
            h, m, s = ln.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError("dur nahi mili")

if __name__ == "__main__":
    meta = []
    for i, (phase, text, q) in enumerate(BEATS):
        out = RUN / f"b{i}.mp3"
        tts._gtts(text, out)
        d = dur_of(out)
        meta.append({"i": i, "phase": phase, "text": text, "q": q,
                     "dur": round(d, 2), "mp3": str(out)})
        print(f"beat{i} [{phase}] {d:.2f}s ✅")
    (RUN / "beats.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print("total narration:", round(sum(m["dur"] for m in meta), 1), "s")
