# EchoScribe

EchoScribe is an offline Windows desktop tool for transcribing local audio/video files and recording system audio. It keeps audio on your computer, uses a bundled `faster-whisper` model, and exports readable transcripts, subtitles, and structured timestamp data.

## Features

- Import local audio or video files and transcribe them offline.
- Record the audio currently playing on the computer.
- Choose automatic language detection, Chinese, or English.
- Export `.txt`, `.srt`, and `.json` for every transcription job.
- Use bundled `ffmpeg.exe` for extraction and format conversion.

EchoScribe v1 does not download videos from Douyin, Bilibili, YouTube, or other platforms. Import downloaded/local files, or use system-audio recording while a video plays.

## Quick Start

1. Unzip the portable package.
2. Run `EchoScribe.exe` when using a packaged build.
3. For development, run:

   ```powershell
   .\scripts\setup_dev.ps1
   .\.venv\Scripts\python.exe -m echoscribe.app
   ```

4. Pick an output folder.
5. Import an audio/video file, or record computer audio.
6. Select language: Auto, Chinese, or English.
7. Click transcribe.

## Outputs

For each job, EchoScribe writes:

- `.txt`: readable transcript with timestamps.
- `.srt`: subtitle file.
- `.json`: structured data with language, duration, and segment timestamps.

## Recommended Hardware

Minimum:

- Windows 10 or Windows 11
- 4-core CPU
- 8 GB RAM
- 2 GB free disk space

Recommended:

- 6-core or better CPU
- 16 GB RAM
- SSD
- 4 GB or more free disk space

The first version runs on CPU with int8 inference. NVIDIA GPU acceleration can be added later.

## Notes

- The bundled `small` model supports Chinese, English, and automatic language detection.
- Domain-specific words, such as finance, medical, or legal terms, may need manual correction.
- Audio quality strongly affects transcript quality.
- System-audio recording captures all audio sent to the default playback device, including notifications.

## Development

```powershell
.\scripts\setup_dev.ps1
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m echoscribe.app
```

To create a portable build:

```powershell
.\scripts\build_portable.ps1
```

