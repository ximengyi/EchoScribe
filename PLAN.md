# EchoScribe Offline Transcription Software Plan

## Summary

EchoScribe is a Windows portable desktop app for offline audio/video transcription. It supports importing local media files, recording system audio, transcribing Chinese or English with `faster-whisper small`, and exporting TXT, SRT, and JSON.

The project lives at `D:\pywork\EchoScribe` and is managed with Git.

## Product Scope

Included in v1:

- Local audio/video import.
- System audio recording.
- Fixed-duration recording.
- Start/stop recording.
- Offline transcription with a bundled model.
- TXT, SRT, and JSON outputs.
- Bundled ffmpeg.

Excluded from v1:

- Downloading videos from platform URLs.
- Account/login automation for video platforms.
- Cloud transcription APIs.
- GPU-specific acceleration UI.

## Model Strategy

The app bundles `faster-whisper small` for offline CPU transcription. Default compute mode is `int8` for reasonable performance on ordinary Windows computers. Language can be automatic, Chinese, or English.

## Packaging Strategy

The first deliverable is a portable zip. It contains the app executable, ffmpeg, model files, runtime dependencies, and documentation. Users unzip and run without installing system-wide dependencies.

## Implementation Notes

- UI: Python Tkinter.
- Media conversion: bundled ffmpeg.
- ASR: faster-whisper.
- Recording: Windows Core Audio loopback via PowerShell-hosted C#.
- Outputs: TXT, SRT, JSON.

## Test Plan

- Transcribe an existing MP3 sample and verify TXT/SRT/JSON.
- Import an MP4 sample and verify audio extraction.
- Record 10 seconds of system audio and verify output is playable.
- Start and stop recording manually and verify WAV header integrity.
- Test paths with Chinese characters, spaces, and long names.
- Confirm the app starts without network access when model files are present.

