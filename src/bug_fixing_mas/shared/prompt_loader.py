from __future__ import annotations

from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROMPTS_DIR = PROJECT_ROOT / "docs" / "prompts"


@lru_cache(maxsize=None)
def load_prompt(prompt_filename: str) -> str:
    """Load an agent prompt from docs/prompts for runtime use."""
    prompt_path = PROMPTS_DIR / prompt_filename
    return prompt_path.read_text(encoding="utf-8").strip()
