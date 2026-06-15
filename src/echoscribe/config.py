from __future__ import annotations

from pathlib import Path
import sys
import time


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
    exe_name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
    bundled = resource_root() / "vendor" / "ffmpeg" / exe_name
    if bundled.exists():
        return bundled

    try:
        import imageio_ffmpeg

        return Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass

    raise FileNotFoundError("ffmpeg not found. Bundle ffmpeg or install imageio-ffmpeg.")


def model_path() -> Path:
    bundled = resource_root() / "vendor" / "models" / "faster-whisper-small"
    if bundled.exists():
        return bundled
    return Path("small")


def default_output_dir() -> Path:
    path = project_root() / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_session_dir(label: str = "session", root: Path | None = None) -> Path:
    safe_label = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in label).strip("_")
    safe_label = safe_label or "session"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    millis = int((time.time() % 1) * 1000)
    root_dir = root or default_output_dir()
    root_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{stamp}-{millis:03d}-{safe_label}"
    for index in range(1000):
        suffix = "" if index == 0 else f"-{index}"
        path = root_dir / f"{base_name}{suffix}"
        try:
            path.mkdir(parents=True, exist_ok=False)
            return path
        except FileExistsError:
            continue
    raise FileExistsError(f"could not create a unique output session directory under {root_dir}")


def recording_script_path() -> Path:
    path = resource_root() / "scripts" / "record_system_audio.ps1"
    if not path.exists():
        raise FileNotFoundError(f"recording script not found: {path}")
    return path
