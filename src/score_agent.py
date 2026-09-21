"""Score Agent — Search Agent ke candidate pool me se BEST asset(s) chunta hai.

Signals (research-backed):
  * vertical orientation hard-preference (Shorts 9:16)
  * resolution area (HD bonus)
  * video dur-fit: clip length ≈ beat length
  * TAG/ALT RELEVANCE: source metadata (pixabay tags, pexels alt) ka overlap
    brief ke vis/search_q tokens se — theme-matching jaisa [vijaxx pipeline]
  * size sanity (dead/corrupt clips door)
  * optional vision-QA semantic boost (keys sirf allowed runs me; fail-open)
A/B mode: top-2 distinct assets → dual-visual split (mid-beat visual switch).
"""
import re

from . import vision_qa


def _tok(s) -> set:
    return set(re.findall(r"[a-z]+", (s or "").lower()))


def _want_tokens(brief: dict) -> set:
    sq = brief.get("search_q", [])
    if isinstance(sq, str):
        sq = [sq]
    return _tok(brief.get("vis", "")) | _tok(" ".join(sq)) | _tok(brief.get("q", ""))


def score(cand: dict, brief: dict, want_dur: float) -> float:
    s = 0.0
    w, h = cand.get("w") or 0, cand.get("h") or 0
    if w and h:
        s += 3.0 if w <= h else -6.0           # vertical hard preference
        s += min(2.0, (w * h) / (1080 * 1920))  # HD bonus
    if cand["type"] == "video":
        d = cand.get("dur") or 5.0
        s += max(0.0, 2.0 - abs(d - want_dur) / max(1.0, want_dur))  # dur-fit
        s += 1.0 if (cand.get("size") or 0) > 200_000 else 0.0       # sanity
    want, have = _want_tokens(brief), _tok(cand.get("tags", ""))
    if want and have:
        s += 2.5 * len(want & have) / min(6.0, len(want))  # relevance
    return round(s, 2)


def pick_best(pool: list, brief: dict, want_dur: float,
              qa: bool = True, two: bool = False) -> list:
    """Score-sorted pool me se best (ya A/B ke liye top-2) QA-passed assets."""
    want = 2 if two else 1
    picks = []
    for c in sorted(pool, key=lambda c: score(c, brief, want_dur), reverse=True)[:4]:
        if qa and not vision_qa.frame_matches(c["path"], brief.get("vis", ""),
                                              str(brief.get("phase", ""))):
            continue
        picks.append(c)
        if len(picks) >= want:
            break
    return picks
