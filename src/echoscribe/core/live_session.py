from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from echoscribe.config import ffmpeg_path, model_path
from echoscribe.core.media import concat_wav_files, convert_to_mp3, mix_audio_files
from echoscribe.core.process import popen_hidden
from echoscribe.core.recorder import SystemAudioRecorder
from echoscribe.core.subtitles import Segment, to_plain_txt, to_srt, to_txt


class LiveMeetingSession:
    def __init__(
        self,
        output_dir: Path,
        language: str | None = None,
        mic_device: str | None = None,
        chunk_seconds: int = 8,
    ) -> None:
        self.output_dir = output_dir
        self.language = language
        self.mic_device = mic_device or os.environ.get("ECHOSCRIBE_MIC_DEVICE") or "麦克风 (Realtek High Definition Audio)"
        self.chunk_seconds = chunk_seconds
        self.session_dir = output_dir / f"live-session-{time.strftime('%Y%m%d-%H%M%S')}"
        self.chunks_dir = self.session_dir / "mic_chunks"
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.system_recorder = SystemAudioRecorder(self.session_dir)
        self.system_wav: Path | None = None
        self.current_mic_process: subprocess.Popen[str] | None = None
        self.model: Any = None
        self.segments: list[Segment] = []
        self.log: list[str] = []
        self.status = "idle"
        self.started_at = 0.0
        self.outputs: dict[str, Path] = {}
        self.error: str | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.started_at = time.time()
        self.status = "recording"
        self._log("实时会议记录已开始。")
        self.system_wav = self.system_recorder.start()
        self._log(f"系统声音录制中: {self.system_wav}")
        self.thread = threading.Thread(target=self._run_mic_loop, daemon=True)
        self.thread.start()

    def stop(self) -> dict[str, Path]:
        self._log("正在停止实时会议记录...")
        self.stop_event.set()
        if self.current_mic_process and self.current_mic_process.poll() is None:
            self.current_mic_process.terminate()
        if self.thread:
            self.thread.join(timeout=self.chunk_seconds + 5)

        system_paths: tuple[Path, Path] | None = None
        try:
            system_paths = self.system_recorder.stop()
            self._log(f"系统声音已保存: {system_paths[1]}")
        except Exception as exc:
            self._log(f"系统声音停止失败: {exc}")

        chunk_paths = [path for path in sorted(self.chunks_dir.glob("mic-*.wav")) if path.stat().st_size > 44]
        if chunk_paths:
            mic_wav = self.session_dir / "microphone.wav"
            concat_wav_files(chunk_paths, mic_wav)
            mic_mp3 = convert_to_mp3(mic_wav, self.session_dir / "microphone.mp3")
            self.outputs["mic_wav"] = mic_wav
            self.outputs["mic_mp3"] = mic_mp3
            self._log(f"麦克风音频已保存: {mic_mp3}")
        else:
            mic_wav = None

        if system_paths:
            self.outputs["system_wav"] = system_paths[0]
            self.outputs["system_mp3"] = system_paths[1]

        mix_inputs = [path for path in [system_paths[0] if system_paths else None, mic_wav] if path]
        if mix_inputs:
            mixed_mp3 = mix_audio_files(mix_inputs, self.session_dir / "meeting-mixed.mp3")
            self.outputs["mixed_mp3"] = mixed_mp3

        self.outputs.update(self._write_transcripts())
        self.status = "stopped"
        self._log("实时会议记录已完成。")
        return self.outputs

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": self.status,
                "log": list(self.log),
                "segments": [asdict(segment) for segment in self.segments],
                "outputs": {key: str(value) for key, value in self.outputs.items()},
                "error": self.error,
            }

    def _run_mic_loop(self) -> None:
        try:
            self._load_model()
            index = 1
            while not self.stop_event.is_set():
                start_offset = max(0.0, time.time() - self.started_at)
                chunk_path = self.chunks_dir / f"mic-{index:04d}.wav"
                self._record_mic_chunk(chunk_path)
                if chunk_path.exists() and chunk_path.stat().st_size > 44:
                    self._transcribe_chunk(chunk_path, start_offset)
                index += 1
        except Exception as exc:
            self.error = str(exc)
            self.status = "failed"
            self._log(f"实时字幕失败: {exc}")

    def _record_mic_chunk(self, chunk_path: Path) -> None:
        command = [
            str(ffmpeg_path()),
            "-hide_banner",
            "-y",
            "-f",
            "dshow",
            "-i",
            f"audio={self.mic_device}",
            "-t",
            str(self.chunk_seconds),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(chunk_path),
        ]
        self.current_mic_process = popen_hidden(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = self.current_mic_process.communicate()
        if self.current_mic_process.returncode not in (0, 255) and not self.stop_event.is_set():
            raise RuntimeError(stderr.strip() or stdout.strip())

    def _load_model(self) -> None:
        if self.model is None:
            from faster_whisper import WhisperModel

            self._log("正在加载实时字幕模型...")
            self.model = WhisperModel(str(model_path()), device="cpu", compute_type="int8")

    def _transcribe_chunk(self, chunk_path: Path, start_offset: float) -> None:
        if self.model is None:
            return
        segments_iter, _ = self.model.transcribe(
            str(chunk_path),
            language=self.language,
            vad_filter=True,
            beam_size=3,
            condition_on_previous_text=False,
        )
        new_segments: list[Segment] = []
        for item in segments_iter:
            text = item.text.strip()
            if text:
                new_segments.append(
                    Segment(start=start_offset + float(item.start), end=start_offset + float(item.end), text=text)
                )
        if new_segments:
            with self._lock:
                self.segments.extend(new_segments)
            for segment in new_segments:
                self._log(f"[{segment.start:0.1f}s] {segment.text}")

    def _write_transcripts(self) -> dict[str, Path]:
        txt_path = self.session_dir / "live-transcript.txt"
        plain_path = self.session_dir / "live-transcript.plain.txt"
        srt_path = self.session_dir / "live-transcript.srt"
        json_path = self.session_dir / "live-transcript.json"
        txt_path.write_text(to_txt(self.segments), encoding="utf-8")
        plain_path.write_text(to_plain_txt(self.segments), encoding="utf-8")
        srt_path.write_text(to_srt(self.segments), encoding="utf-8")
        json_path.write_text(
            json.dumps({"segments": [asdict(segment) for segment in self.segments]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"live_txt": txt_path, "live_plain_txt": plain_path, "live_srt": srt_path, "live_json": json_path}

    def _log(self, message: str) -> None:
        with self._lock:
            self.log.append(message)
