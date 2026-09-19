"""Config: env + niche YAML loader. Saare paths yahi se milte hain."""
import os
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
STATE = ROOT / "state"
RUN = ROOT / "output"


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_niche(name: str | None = None) -> dict:
    name = name or env("NICHE", "hindi_agriculture")
    path = ROOT / "niches" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"niche file nahi mili: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def font(display: bool = False) -> str:
    """Devanagari fonts. display=True → Baloo 2 (bold headings/thumbnail)."""
    return str(FONTS / ("Baloo2-Bold.ttf" if display else "NotoSansDevanagari-Bold.ttf"))
