from __future__ import annotations

from pathlib import Path
import sys


APP_NAME = "EchoScribe"


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return project_root()


def ffmpeg_path() -> Path:
    bundled = resource_root() / "vendor" / "ffmpeg" / "ffmpeg.exe"
    if bundled.exists():
        return bundled
    raise FileNotFoundError(f"ffmpeg.exe not found: {bundled}")


def model_path() -> Path:
    bundled = resource_root() / "vendor" / "models" / "faster-whisper-small"
    if bundled.exists():
        return bundled
    return Path("small")


def default_output_dir() -> Path:
    path = project_root() / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def recording_script_path() -> Path:
    path = resource_root() / "scripts" / "record_system_audio.ps1"
    if not path.exists():
        raise FileNotFoundError(f"recording script not found: {path}")
    return path
