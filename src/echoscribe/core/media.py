from __future__ import annotations

import subprocess
from pathlib import Path

from echoscribe.config import ffmpeg_path


AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v"}


def is_supported_media(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def safe_stem(path: Path) -> str:
    stem = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in path.stem)
    return stem.strip("_") or "media"


def extract_audio(input_path: Path, work_dir: Path) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if not is_supported_media(input_path):
        raise ValueError(f"Unsupported media type: {input_path.suffix}")

    work_dir.mkdir(parents=True, exist_ok=True)
    output_path = work_dir / f"{safe_stem(input_path)}.transcribe.wav"
    command = [
        str(ffmpeg_path()),
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr.strip()}")
    return output_path


def convert_to_mp3(input_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg_path()),
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg MP3 conversion failed:\n{result.stderr.strip()}")
    return output_path


def concat_wav_files(input_paths: list[Path], output_path: Path) -> Path:
    if not input_paths:
        raise ValueError("no audio chunks to concatenate")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_path = output_path.with_suffix(".concat.txt")
    lines = [f"file '{path.resolve().as_posix()}'" for path in input_paths]
    list_path.write_text("\n".join(lines), encoding="utf-8")
    command = [
        str(ffmpeg_path()),
        "-hide_banner",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{result.stderr.strip()}")
    return output_path


def mix_audio_files(input_paths: list[Path], output_path: Path) -> Path:
    if not input_paths:
        raise ValueError("no audio files to mix")
    if len(input_paths) == 1:
        return convert_to_mp3(input_paths[0], output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [str(ffmpeg_path()), "-hide_banner", "-y"]
    for path in input_paths:
        command.extend(["-i", str(path)])
    command.extend(
        [
            "-filter_complex",
            f"amix=inputs={len(input_paths)}:duration=longest:normalize=0",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(output_path),
        ]
    )
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mix failed:\n{result.stderr.strip()}")
    return output_path
