from __future__ import annotations

from pathlib import Path


LANGUAGE_CHOICES = {
    "Auto": None,
    "Chinese": "zh",
    "English": "en",
}


def normalize_output_dir(path: str | Path) -> Path:
    output_dir = Path(path).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

