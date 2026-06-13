from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from echoscribe.config import APP_NAME, default_output_dir
from echoscribe.core.jobs import LANGUAGE_CHOICES, normalize_output_dir
from echoscribe.core.recorder import SystemAudioRecorder
from echoscribe.core.transcriber import Transcriber


class EchoScribeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("820x560")
        self.minsize(760, 500)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.output_dir = tk.StringVar(value=str(default_output_dir()))
        self.language = tk.StringVar(value="Auto")
        self.fixed_seconds = tk.IntVar(value=60)
        self.selected_file: Path | None = None
        self.recorder = SystemAudioRecorder(default_output_dir())
        self.last_recorded_mp3: Path | None = None

        self._build()
        self.after(100, self._drain_events)

    def _build(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        top = ttk.LabelFrame(root, text="Settings", padding=12)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Output folder").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.output_dir).grid(row=0, column=1, sticky=tk.EW, padx=8)
        ttk.Button(top, text="Browse", command=self.choose_output_dir).grid(row=0, column=2)

        ttk.Label(top, text="Language").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Combobox(top, textvariable=self.language, values=list(LANGUAGE_CHOICES), state="readonly", width=16).grid(
            row=1, column=1, sticky=tk.W, padx=8, pady=(10, 0)
        )
        top.columnconfigure(1, weight=1)

        actions = ttk.LabelFrame(root, text="Actions", padding=12)
        actions.pack(fill=tk.X, pady=12)

        ttk.Button(actions, text="Import audio/video", command=self.choose_media).grid(row=0, column=0, sticky=tk.EW)
        ttk.Button(actions, text="Transcribe selected file", command=self.transcribe_selected).grid(
            row=0, column=1, sticky=tk.EW, padx=8
        )
        self.file_label = ttk.Label(actions, text="No file selected")
        self.file_label.grid(row=0, column=2, sticky=tk.W)

        ttk.Label(actions, text="Fixed recording seconds").grid(row=1, column=0, sticky=tk.W, pady=(12, 0))
        ttk.Spinbox(actions, from_=1, to=86400, textvariable=self.fixed_seconds, width=10).grid(
            row=1, column=1, sticky=tk.W, padx=8, pady=(12, 0)
        )
        ttk.Button(actions, text="Record fixed duration", command=self.record_fixed).grid(
            row=1, column=2, sticky=tk.W, pady=(12, 0)
        )

        ttk.Button(actions, text="Start recording", command=self.start_recording).grid(row=2, column=0, sticky=tk.EW, pady=(12, 0))
        ttk.Button(actions, text="Stop recording", command=self.stop_recording).grid(row=2, column=1, sticky=tk.EW, padx=8, pady=(12, 0))
        ttk.Button(actions, text="Transcribe last recording", command=self.transcribe_last_recording).grid(
            row=2, column=2, sticky=tk.W, pady=(12, 0)
        )

        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)

        log_frame = ttk.LabelFrame(root, text="Log", padding=12)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(log_frame, height=14, wrap=tk.WORD)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.configure(yscrollcommand=scrollbar.set)

        self.status = ttk.Label(root, text="Ready")
        self.status.pack(fill=tk.X, pady=(8, 0))

    def choose_output_dir(self) -> None:
        path = filedialog.askdirectory(initialdir=self.output_dir.get())
        if path:
            self.output_dir.set(path)
            self.recorder = SystemAudioRecorder(Path(path))

    def choose_media(self) -> None:
        filetypes = [
            ("Media files", "*.mp4 *.mov *.mkv *.avi *.webm *.flv *.wmv *.m4v *.wav *.mp3 *.m4a *.aac *.flac *.ogg *.opus *.wma"),
            ("All files", "*.*"),
        ]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.selected_file = Path(path)
            self.file_label.configure(text=str(self.selected_file))
            self._log(f"Selected file: {self.selected_file}")

    def transcribe_selected(self) -> None:
        if not self.selected_file:
            messagebox.showwarning(APP_NAME, "Please select a media file first.")
            return
        self._run_background(lambda: self._transcribe_path(self.selected_file))

    def transcribe_last_recording(self) -> None:
        if not self.last_recorded_mp3:
            messagebox.showwarning(APP_NAME, "No recording is available yet.")
            return
        self._run_background(lambda: self._transcribe_path(self.last_recorded_mp3))

    def record_fixed(self) -> None:
        seconds = int(self.fixed_seconds.get())
        self._run_background(lambda: self._record_fixed(seconds))

    def start_recording(self) -> None:
        try:
            self.recorder = SystemAudioRecorder(normalize_output_dir(self.output_dir.get()))
            wav_path = self.recorder.start()
            self._log(f"Recording started: {wav_path}")
            self.status.configure(text="Recording...")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def stop_recording(self) -> None:
        self._run_background(self._stop_recording)

    def _record_fixed(self, seconds: int) -> None:
        self._event("log", f"Recording system audio for {seconds} seconds...")
        self.recorder = SystemAudioRecorder(normalize_output_dir(self.output_dir.get()))
        wav_path, mp3_path = self.recorder.record_fixed(seconds)
        self.last_recorded_mp3 = mp3_path
        self._event("log", f"Recorded WAV: {wav_path}")
        self._event("log", f"Recorded MP3: {mp3_path}")

    def _stop_recording(self) -> None:
        self._event("log", "Stopping recording...")
        wav_path, mp3_path = self.recorder.stop()
        self.last_recorded_mp3 = mp3_path
        self._event("log", f"Recorded WAV: {wav_path}")
        self._event("log", f"Recorded MP3: {mp3_path}")

    def _transcribe_path(self, path: Path) -> None:
        output_dir = normalize_output_dir(self.output_dir.get())
        language = LANGUAGE_CHOICES[self.language.get()]
        transcriber = Transcriber(progress=lambda message: self._event("log", message))
        result = transcriber.transcribe_media(path, output_dir, language=language)
        for kind, output_path in result.items():
            self._event("log", f"{kind.upper()}: {output_path}")

    def _run_background(self, target) -> None:
        self.status.configure(text="Working...")
        thread = threading.Thread(target=self._background_wrapper, args=(target,), daemon=True)
        thread.start()

    def _background_wrapper(self, target) -> None:
        try:
            target()
            self._event("status", "Ready")
        except Exception as exc:
            self._event("error", str(exc))
            self._event("status", "Ready")

    def _event(self, kind: str, payload: object) -> None:
        self.events.put((kind, payload))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._log(str(payload))
            elif kind == "status":
                self.status.configure(text=str(payload))
            elif kind == "error":
                self._log(f"ERROR: {payload}")
                messagebox.showerror(APP_NAME, str(payload))
        self.after(100, self._drain_events)

    def _log(self, message: str) -> None:
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)


def run_app() -> None:
    app = EchoScribeApp()
    app.mainloop()

