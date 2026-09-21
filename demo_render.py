"""Demo assemble — vision-verified images + gTTS narration + phase-aware edit."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, "/home/user/hindi-shorts-bot")
from src import render, visuals

RUN = Path("/home/user/hindi-shorts-bot/demo_run")
ROOT = Path("/home/user/hindi-shorts-bot")
WS = Path("/home/user")
beats = json.loads((RUN / "beats.json").read_text())
niche = yaml.safe_load((ROOT / "niches/hindi_agriculture.yaml").read_text())
pal = niche["visuals"]["color_palette"]

# vision-verified picks (main read_file se check kar chuka hoon)
PICKS = {
    0: "hindi-shorts-bot/demo_run/cand200_0.jpg",          # indian farmer, paddy
    1: "hindi-shorts-bot/demo_run/cand201_0.jpg",          # aerial ploughing
    2: "hindi-shorts-bot/demo_run/cand202_0.jpg",          # bullock mouldboard plough
    3: "hindi-shorts-bot/demo_run/cand203_2.jpg",            # sunset harrowing, dust
    4: "image-search/no-tillage-seed-drill-sowing-machine-fie-1.webp", # seed drill
    5: "image-search/healthy-plant-roots-dark-moist-soil-clos-1.jpg",  # seedling soil
    6: "hindi-shorts-bot/demo_run/cand206_0.jpg",          # cracked dry soil
    7: "hindi-shorts-bot/demo_run/cand207_0.jpg",          # student exam
}

# 1) narration concat
lst = RUN / "narr_list.txt"
lst.write_text("".join(f"file '{RUN / f'b{b['i']}.mp3'}'\n" for b in beats))
subprocess.run([render.ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0",
                "-i", str(lst), "-c", "copy", str(RUN / "narration.mp3")],
               capture_output=True, timeout=120, check=True)

# 2) scenes
scenes = []
for b in beats:
    if b["i"] == 8:   # CTA → designed end-card (sharp 1080x1920 text)
        cta = "फॉलो करें Agri Learning Point\nSHARE + SUBSCRIBE"
        f = visuals.card(cta, pal, RUN / "endcard.png", big=True)
    else:
        src = WS / PICKS[b["i"]]
        dst = RUN / f"img{b['i']}{src.suffix}"
        shutil.copy(src, dst)
        f = {"type": "image", "path": dst, "static": False}
    f["dur"] = b["dur"]
    f["phase"] = b["phase"]
    scenes.append(f)

# 3) render with ducked BGM + whoosh + progress
music = ROOT / "assets" / "music" / "Folk Round.mp3"
out = render.render(scenes, RUN / "narration.mp3", RUN / "demo_tillage.mp4",
                    music=music, seed="tillage-demo")
print("DEMO READY:", out, out.stat().st_size, "bytes")
