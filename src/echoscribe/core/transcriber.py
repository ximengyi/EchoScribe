from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from echoscribe.config import model_path
from echoscribe.core.media import extract_audio, safe_stem
from echoscribe.core.subtitles import Segment, to_plain_txt, to_srt, to_txt


ProgressCallback = Callable[[str], None]


class Transcriber:
    def __init__(self, progress: ProgressCallback | None = None) -> None:
        self._model = None
        self._progress = progress or (lambda message: None)

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._progress("Loading faster-whisper small model...")
            self._model = WhisperModel(str(model_path()), device="cpu", compute_type="int8")
        return self._model

    def transcribe_media(self, input_path: Path, output_dir: Path, language: str | None = None) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        work_dir = output_dir / ".echoscribe_work"
        self._progress("Extracting audio with ffmpeg...")
        audio_path = extract_audio(input_path, work_dir)
        return self.transcribe_audio(audio_path, output_dir, base_name=safe_stem(input_path), language=language)

    def transcribe_audio(
        self,
        audio_path: Path,
        output_dir: Path,
        base_name: str | None = None,
        language: str | None = None,
    ) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        model = self._load_model()
        self._progress("Transcribing audio...")

        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=True,
            beam_size=5,
            condition_on_previous_text=True,
        )

        segments: list[Segment] = []
        for item in segments_iter:
            text = item.text.strip()
            if text:
                segments.append(Segment(start=float(item.start), end=float(item.end), text=text))
                self._progress(f"Recognized {len(segments)} segment(s)...")

        stem = base_name or safe_stem(audio_path)
        txt_path = output_dir / f"{stem}.transcript.txt"
        plain_txt_path = output_dir / f"{stem}.transcript.plain.txt"
        srt_path = output_dir / f"{stem}.transcript.srt"
        json_path = output_dir / f"{stem}.transcript.json"

        txt_path.write_text(to_txt(segments), encoding="utf-8")
        plain_txt_path.write_text(to_plain_txt(segments), encoding="utf-8")
        srt_path.write_text(to_srt(segments), encoding="utf-8")
        json_path.write_text(
            json.dumps(
                {
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "duration": info.duration,
                    "segments": [asdict(segment) for segment in segments],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self._progress("Transcription complete.")
        return {"txt": txt_path, "plain_txt": plain_txt_path, "srt": srt_path, "json": json_path}
