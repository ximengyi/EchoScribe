from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def platform_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower().replace("amd64", "x64").replace("x86_64", "x64")
    if system == "darwin":
        system = "macos"
    return f"{system}-{machine}"


def data_arg(source: Path, target: str) -> str:
    return f"{source}{os.pathsep}{target}"


def main() -> int:
    app_name = "EchoScribe"
    assets = ROOT / ".venv" / "Lib" / "site-packages" / "faster_whisper" / "assets"
    if not assets.exists():
        import faster_whisper

        assets = Path(faster_whisper.__file__).resolve().parent / "assets"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--windowed",
        "--name",
        app_name,
        "--paths",
        str(ROOT / "src"),
        "--add-data",
        data_arg(ROOT / "vendor", "vendor"),
        "--add-data",
        data_arg(ROOT / "scripts" / "record_system_audio.ps1", "scripts"),
        "--add-data",
        data_arg(assets, str(Path("faster_whisper") / "assets")),
        str(ROOT / "src" / "echoscribe" / "app_web.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)

    dist_dir = ROOT / "dist"
    app_dir = dist_dir / app_name
    archive_base = dist_dir / f"{app_name}-{platform_name()}"
    archive = shutil.make_archive(str(archive_base), "zip", app_dir)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
