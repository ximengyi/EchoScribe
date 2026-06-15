from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from echoscribe.config import recording_script_path
from echoscribe.core.media import convert_to_mp3
from echoscribe.core.process import popen_hidden, run_hidden


class SystemAudioRecorder:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.process: subprocess.Popen[str] | None = None
        self.stop_file: Path | None = None
        self.wav_path: Path | None = None

    def _new_paths(self) -> tuple[Path, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        wav_path = self.output_dir / f"system-audio-{stamp}.wav"
        stop_file = self.output_dir / f"system-audio-{stamp}.stop"
        return wav_path, stop_file

    def record_fixed(self, seconds: int) -> tuple[Path, Path]:
        self._ensure_windows_recording()
        if seconds <= 0:
            raise ValueError("seconds must be greater than zero")
        wav_path, _ = self._new_paths()
        command = [
            "powershell",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(recording_script_path()),
            "-OutputPath",
            str(wav_path),
            "-Seconds",
            str(seconds),
            "-Role",
            "Multimedia",
        ]
        result = run_hidden(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        mp3_path = convert_to_mp3(wav_path, wav_path.with_suffix(".mp3"))
        return wav_path, mp3_path

    def start(self) -> Path:
        self._ensure_windows_recording()
        if self.process and self.process.poll() is None:
            raise RuntimeError("recording is already running")

        self.wav_path, self.stop_file = self._new_paths()
        if self.stop_file.exists():
            self.stop_file.unlink()

        command = [
            "powershell",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(recording_script_path()),
            "-OutputPath",
            str(self.wav_path),
            "-StopFile",
            str(self.stop_file),
            "-Role",
            "Multimedia",
        ]
        self.process = popen_hidden(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return self.wav_path

    def stop(self) -> tuple[Path, Path]:
        self._ensure_windows_recording()
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("recording is not running")
        if not self.stop_file or not self.wav_path:
            raise RuntimeError("recording paths are not initialized")

        self.stop_file.write_text("stop", encoding="utf-8")
        stdout, stderr = self.process.communicate(timeout=30)
        if self.process.returncode != 0:
            raise RuntimeError(stderr.strip() or stdout.strip())
        if self.stop_file.exists():
            self.stop_file.unlink()
        mp3_path = convert_to_mp3(self.wav_path, self.wav_path.with_suffix(".mp3"))
        return self.wav_path, mp3_path

    @staticmethod
    def _ensure_windows_recording() -> None:
        if not sys.platform.startswith("win"):
            raise RuntimeError("System audio recording is currently supported on Windows only.")
