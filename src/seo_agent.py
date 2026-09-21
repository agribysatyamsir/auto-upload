"""SEO Agent — topic-wise PROFESSIONAL + TRENDING SEO pack.

knowledge/seo_playbook.md ke structure se: title (core-keyword-first + exam
suffix), description (hook → overview → bullets → note-nudge → FIXED join
block → hashtags → tags → keywords), YouTube tags ≤500 chars.
Join-platforms HAR video me SAME (yaml seo.join_block).
LLM fail/invalid → deterministic FALLBACK (upload kabhi nahi rukta).
"""
import hashlib
import json
import re

from . import config, llm

KB = config.ROOT / "knowledge" / "seo_playbook.md"


def _cfg(niche: dict) -> dict:
    return niche.get("seo", {})


def _seed(topic: str) -> int:
    return int(hashlib.md5(topic.encode()).hexdigest(), 16)


def _suffix(topic: str, cfg: dict) -> str:
    sufs = cfg.get("title_suffixes", ["AGTA & AFO"])
    return sufs[_seed(topic) % len(sufs)]


def _trending(topic: str, cfg: dict, n: int = 3) -> list:
    pool = cfg.get("trending_pool", [])
    i = _seed(topic)
    return [pool[(i + k) % len(pool)] for k in range(min(n, len(pool)))] if pool else []


def _base_title(topic: str, cfg: dict) -> str:
    head, _, rest = topic.partition("–")
    t = f"{head.strip()} in Agriculture: {rest.strip()}" if rest.strip() else \
        f"{topic} in Agriculture: Types, Advantages & Disadvantages"
    return f"{t} | {_suffix(topic, cfg)}"[:100]


def fallback_seo(topic: str, niche: dict) -> dict:
    """LLM ke bina bhi professional pack — deterministic."""
    cfg = _cfg(niche)
    title = _base_title(topic, cfg)
    head, _, rest = topic.partition("–")
    core = head.strip().lower()
    exams = cfg.get("exams", ["UPSSSC AGTA", "IBPS AFO", "ICAR JRF"])
    trend = _trending(topic, cfg, 3)
    bullets = [
        f"Definition, core objectives and practical importance of {core}",
        f"Complete classification with solved examples ({rest.strip() or 'types & methods'})",
        f"Key mechanisms, benefits and field-level applications",
        f"Limitations, common confusion points and exam traps",
        "High-probability MCQs and expected questions for upcoming exams",
    ]
    hook = (f"Are you preparing for {exams[0]} or {exams[1]} and often get confused "
            f"about {core}? In this video, we break down {core} with clear "
            f"classification and exam-oriented points in under 15 minutes. "
            f"Watch till the end to master this topic and secure full marks!")
    overview = (f"Master the complete concept of {title.split(':')[0]}, "
                f"frequently asked in {', '.join(exams)} examinations. This "
                f"structured session gives complete conceptual clarity with "
                f"exam-oriented points.")
    words = re.findall(r"[A-Za-z]+", core)
    hashtags = ["#" + "".join(w.capitalize() for w in words[:2]) or "#Agriculture",
                "#Agronomy", "#Agriculture", "#AgricultureExams",
                "#UPSSSCAGTA", "#IBPSAFO", "#ICARJRF", "#NABARDGradeA",
                "#SoilScience", "#AgriLearningPoint", "#FarmScience"]
    hashtags = [h for h in hashtags if len(h) > 1][:12]
    tags = ([f"{core}", f"types of {core}", f"{core} advantages",
             f"{core} disadvantages", f"{core} notes",
             "upsssc agta agronomy", "ibps afo preparation", "icar jrf agronomy",
             "nabard grade a agriculture", "agriculture competitive exams",
             "agronomy mcqs for competitive exams", "agriculture field officer preparation"]
            + trend)
    tags = _fit_tags(tags)
    keywords = ([f"{core} in agriculture", f"types of {core}",
                 f"advantages and disadvantages of {core}", f"{core} mcq",
                 f"{core} for competitive exams", "agriculture gk",
                 "agronomy lecture", "agricultural science",
                 "upsssc agta agriculture classes", "bpsc bao agriculture",
                 "fci agriculture syllabus", "dryland farming practices"]
                + trend)
    desc = _assemble(hook, overview, bullets, niche, hashtags, tags, keywords)
    return {"title": title, "description": desc, "tags": tags,
            "hashtags": hashtags, "keywords": keywords}


def _fit_tags(tags: list, limit: int = 490) -> list:
    out, used = [], 0
    for t in tags:
        t = str(t).strip().strip("#").strip().lower()
        t = " ".join(t.split())
        if not t or len(t) < 2 or len(t) > 60 or t in out:
            continue
        if used + len(t) + 2 > limit:
            break
        out.append(t)
        used += len(t) + 2
    return out[:30]


def _norm_list(v, fallback: list) -> list:
    """LLM kabhi str de de, kabhi list — YouTube invalidTags se bachao."""
    if isinstance(v, str):
        v = [x for x in v.replace("\n", ",").split(",")]
    if not isinstance(v, list):
        v = fallback
    out, seen = [], set()
    for x in v:
        x = " ".join(str(x).split()).strip()
        if x and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return out


def _assemble(hook, overview, bullets, niche, hashtags, tags, keywords) -> str:
    cfg = _cfg(niche)
    join = cfg.get("join_block", "").strip()
    bl = "\n".join(f"• {b}" for b in bullets)
    parts = [hook.strip(), overview.strip(),
             "In this detailed lecture, we cover:", "", bl, "",
             "Take notes of critical data points and stay ahead of the "
             "competition!", "", join, "",
             " ".join(hashtags), "", ", ".join(tags), "", ", ".join(keywords)]
    return "\n".join(parts)[:4800]


def build_seo(topic: str, niche: dict, sc: dict | None = None) -> dict:
    """LLM-seo with playbook; validation fail → fallback."""
    cfg = _cfg(niche)
    try:
        kb = KB.read_text(encoding="utf-8")
        out = llm.generate(
            f"{kb}\n\n---\nTOPIC: {topic}\n"
            f"TITLE_SUFFIX is fixed: {_suffix(topic, cfg)} (title me yahi use karo)\n"
            f"EXAMS: {cfg.get('exams', [])}\nTRENDING_POOL: {cfg.get('trending_pool', [])}\n"
            f"Script beats (context): {json.dumps([b.get('t', '') for b in (sc or {}).get('beats', [])][:6], ensure_ascii=False)}\n\n"
            f'SIRF JSON do: {{"title":"...","hook":"para1","overview":"para2",'
            f'"bullets":["5-7"],"hashtags":["#..."],"tags":["30"],"keywords":["35"]}}')
        title = " ".join(str(out.get("title", "")).split())[:100]
        bullets = _norm_list(out.get("bullets"), [])[:8]
        tags = _fit_tags(_norm_list(out.get("tags"), []))
        hashtags = _norm_list(out.get("hashtags"), [])
        hashtags = [h if h.startswith("#") else "#" + h for h in hashtags][:12]
        keywords = _norm_list(out.get("keywords"), [])[:40]
        trend = _trending(topic, cfg, 3)
        blob = " ".join(tags + keywords).lower()
        for tr in trend:                       # trending tokens LAZMI
            if tr.lower() not in blob:
                keywords.append(tr)
        if ("|" not in title or len(bullets) < 4 or len(tags) < 8
                or len(hashtags) < 6):
            raise ValueError("seo invalid")
        desc = _assemble(out.get("hook", ""), out.get("overview", ""), bullets,
                         niche, hashtags, tags, keywords)
        print(f"[seo] LLM pack ✅ title: {title}")
        return {"title": title, "description": desc, "tags": tags,
                "hashtags": hashtags, "keywords": keywords}
    except Exception as e:
        print(f"[seo] fallback ({str(e)[:50]})")
        return fallback_seo(topic, niche)
