from __future__ import annotations

import shutil
from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "vendor" / "models" / "faster-whisper-small"


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists() and (TARGET / "model.bin").exists():
        print(f"Model already exists: {TARGET}")
        return 0

    downloaded = Path(snapshot_download("Systran/faster-whisper-small"))
    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(downloaded, TARGET)
    print(f"Model copied to: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
