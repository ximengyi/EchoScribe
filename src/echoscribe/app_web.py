from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from echoscribe.config import APP_NAME, default_output_dir
from echoscribe.core.jobs import LANGUAGE_CHOICES, normalize_output_dir
from echoscribe.core.live_session import LiveMeetingSession
from echoscribe.core.recorder import SystemAudioRecorder
from echoscribe.core.transcriber import Transcriber


JOBS: dict[str, dict[str, Any]] = {}
RECORDER: SystemAudioRecorder | None = None
LAST_RECORDING: Path | None = None
LIVE_SESSION: LiveMeetingSession | None = None


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EchoScribe</title>
  <style>
    body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: #f5f7fb; color: #172033; }
    main { max-width: 960px; margin: 0 auto; padding: 28px; }
    h1 { margin: 0 0 4px; font-size: 30px; }
    p { color: #59657a; }
    section { background: #fff; border: 1px solid #e0e6f0; border-radius: 8px; padding: 18px; margin: 16px 0; }
    label { display: block; font-weight: 600; margin: 12px 0 6px; }
    input, select, button { font: inherit; }
    input[type="number"], select { padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; }
    input[type="file"] { display: block; }
    button { padding: 9px 14px; border: 0; border-radius: 6px; background: #2563eb; color: white; cursor: pointer; margin-right: 8px; }
    button.secondary { background: #475569; }
    button:disabled { background: #94a3b8; cursor: wait; }
    #log { white-space: pre-wrap; background: #0f172a; color: #dbeafe; border-radius: 8px; padding: 14px; min-height: 180px; overflow: auto; }
    #liveCaptions { white-space: pre-wrap; background: #111827; color: #f8fafc; border-radius: 8px; padding: 14px; min-height: 160px; overflow: auto; font-size: 17px; line-height: 1.6; }
    .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .muted { color: #64748b; font-size: 13px; }
    .status { display: inline-flex; align-items: center; gap: 8px; margin-top: 12px; padding: 10px 12px; border-radius: 8px; background: #ecfdf5; color: #166534; font-weight: 700; }
    .status.recording { background: #fef2f2; color: #b91c1c; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: currentColor; display: inline-block; }
    .recording .dot { animation: pulse 1s infinite; }
    .tabs { display: flex; gap: 8px; margin: 4px 0 14px; border-bottom: 1px solid #d8e1ee; }
    .tab-button { border: 1px solid transparent; border-bottom: 0; border-radius: 8px 8px 0 0; background: transparent; color: #475569; padding: 10px 16px; margin: 0; font-weight: 700; }
    .tab-button.active { background: #fff; color: #1d4ed8; border-color: #d8e1ee; box-shadow: 0 -1px 0 #fff inset; }
    .tab-button:hover { background: #eff6ff; color: #1d4ed8; }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: .35; transform: scale(1.4); } }
    a { color: #2563eb; }
  </style>
</head>
<body>
  <main>
    <h1>EchoScribe</h1>
    <p>离线音视频转文字工具。本地运行，不上传到外部服务。</p>

    <section>
      <h2>导入音频 / 视频转写</h2>
      <label>语言</label>
      <select id="language">
        <option value="Auto">Auto</option>
        <option value="Chinese">Chinese</option>
        <option value="English">English</option>
      </select>
      <label>选择文件</label>
      <input id="file" type="file">
      <p class="muted">支持 mp4、mkv、mp3、wav、m4a、flac 等常见格式。</p>
      <button id="transcribeBtn" onclick="transcribeUpload()">上传并转写</button>
    </section>

    <section>
      <div class="tabs" role="tablist" aria-label="录制功能">
        <button id="recordTab" class="tab-button active" role="tab" aria-selected="true" aria-controls="recordPanel" onclick="showRecordTab('record')">录制电脑声音</button>
        <button id="liveTab" class="tab-button" role="tab" aria-selected="false" aria-controls="livePanel" onclick="showRecordTab('live')">实时会议记录</button>
      </div>

      <div id="recordPanel" class="tab-panel active" role="tabpanel" aria-labelledby="recordTab">
        <h2>录制电脑声音</h2>
        <div class="row">
          <label>固定录制秒数 <input id="seconds" type="number" min="1" value="60"></label>
          <button onclick="recordFixed()">固定时长录制</button>
        </div>
        <div class="row">
          <button id="startBtn" onclick="recordStart()">开始录制</button>
          <button id="stopBtn" class="secondary" onclick="recordStop()">停止录制</button>
          <button id="transcribeRecordingBtn" onclick="transcribeLastRecording()">转写最后一次录音</button>
        </div>
        <div id="recordStatus" class="status"><span class="dot"></span><span id="recordStatusText">未在录制</span></div>
        <p id="lastRecording" class="muted">还没有录制文件。录制完成后会自动加载到“转写最后一次录音”。</p>
      </div>

      <div id="livePanel" class="tab-panel" role="tabpanel" aria-labelledby="liveTab">
        <h2>实时会议记录</h2>
        <p class="muted">同时录制电脑扬声器声音和麦克风声音；麦克风会按片段实时转写并显示在这里。停止后自动生成音频和记录文件。</p>
        <div class="row">
          <button id="liveStartBtn" onclick="liveStart()">开始实时记录</button>
          <button id="liveStopBtn" class="secondary" onclick="liveStop()">停止并生成文件</button>
        </div>
        <div id="liveStatus" class="status"><span class="dot"></span><span id="liveStatusText">未在实时记录</span></div>
        <label>实时字幕</label>
        <div id="liveCaptions">等待开始...</div>
      </div>
    </section>

    <section>
      <h2>任务日志</h2>
      <div id="log">Ready.</div>
    </section>
  </main>
<script>
let currentJob = null;
let recordingStartedAt = null;
let recordingTimer = null;
let lastRecordingPath = null;
let livePollTimer = null;

function log(msg) {
  const el = document.getElementById('log');
  el.textContent += "\n" + msg;
  el.scrollTop = el.scrollHeight;
}

function language() {
  return encodeURIComponent(document.getElementById('language').value);
}

function showRecordTab(tab) {
  const isLive = tab === 'live';
  document.getElementById('recordTab').classList.toggle('active', !isLive);
  document.getElementById('liveTab').classList.toggle('active', isLive);
  document.getElementById('recordPanel').classList.toggle('active', !isLive);
  document.getElementById('livePanel').classList.toggle('active', isLive);
  document.getElementById('recordTab').setAttribute('aria-selected', String(!isLive));
  document.getElementById('liveTab').setAttribute('aria-selected', String(isLive));
}

function setRecordingState(isRecording, detail) {
  const box = document.getElementById('recordStatus');
  const text = document.getElementById('recordStatusText');
  box.className = isRecording ? 'status recording' : 'status';
  text.textContent = detail || (isRecording ? '正在录制...' : '未在录制');
  document.getElementById('startBtn').disabled = isRecording;
  document.getElementById('stopBtn').disabled = !isRecording;
}

function startRecordingTimer() {
  recordingStartedAt = Date.now();
  if (recordingTimer) clearInterval(recordingTimer);
  recordingTimer = setInterval(() => {
    if (!recordingStartedAt) return;
    const elapsed = Math.floor((Date.now() - recordingStartedAt) / 1000);
    const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const ss = String(elapsed % 60).padStart(2, '0');
    setRecordingState(true, '正在录制... ' + mm + ':' + ss);
  }, 500);
}

function stopRecordingTimer() {
  recordingStartedAt = null;
  if (recordingTimer) clearInterval(recordingTimer);
  recordingTimer = null;
}

function setLastRecording(path) {
  lastRecordingPath = path;
  document.getElementById('lastRecording').textContent = '最后一次录音已加载: ' + path;
  document.getElementById('transcribeRecordingBtn').disabled = false;
}

function setLiveState(isRecording, detail) {
  const box = document.getElementById('liveStatus');
  const text = document.getElementById('liveStatusText');
  box.className = isRecording ? 'status recording' : 'status';
  text.textContent = detail || (isRecording ? '正在实时记录...' : '未在实时记录');
  document.getElementById('liveStartBtn').disabled = isRecording;
  document.getElementById('liveStopBtn').disabled = !isRecording;
}

async function transcribeUpload() {
  const file = document.getElementById('file').files[0];
  if (!file) { alert('请先选择文件'); return; }
  document.getElementById('transcribeBtn').disabled = true;
  log('Uploading: ' + file.name);
  const res = await fetch('/api/transcribe-upload?language=' + language(), {
    method: 'POST',
    headers: {'X-Filename': encodeURIComponent(file.name)},
    body: file
  });
  const data = await res.json();
  document.getElementById('transcribeBtn').disabled = false;
  if (!data.ok) { log('ERROR: ' + data.error); return; }
  watchJob(data.job_id);
}

async function recordFixed() {
  const seconds = document.getElementById('seconds').value || '60';
  setRecordingState(true, '正在固定时长录制... 预计 ' + seconds + ' 秒');
  const res = await fetch('/api/record-fixed?seconds=' + encodeURIComponent(seconds), {method: 'POST'});
  const data = await res.json();
  if (!data.ok) { setRecordingState(false, '录制失败'); log('ERROR: ' + data.error); return; }
  watchJob(data.job_id);
}

async function recordStart() {
  const res = await fetch('/api/record-start', {method: 'POST'});
  const data = await res.json();
  if (data.ok) {
    log('Recording started: ' + data.wav);
    setRecordingState(true, '正在录制... 00:00');
    startRecordingTimer();
  } else {
    log('ERROR: ' + data.error);
  }
}

async function recordStop() {
  const res = await fetch('/api/record-stop', {method: 'POST'});
  const data = await res.json();
  if (!data.ok) { log('ERROR: ' + data.error); return; }
  stopRecordingTimer();
  setRecordingState(false, '录制完成');
  setLastRecording(data.mp3);
  log('Recorded MP3: ' + data.mp3);
}

async function transcribeLastRecording() {
  const res = await fetch('/api/transcribe-last-recording?language=' + language(), {method: 'POST'});
  const data = await res.json();
  if (!data.ok) { log('ERROR: ' + data.error); return; }
  watchJob(data.job_id);
}

async function liveStart() {
  const res = await fetch('/api/live-start?language=' + language(), {method: 'POST'});
  const data = await res.json();
  if (!data.ok) { log('ERROR: ' + data.error); return; }
  document.getElementById('liveCaptions').textContent = '实时记录已开始，等待第一段字幕...';
  setLiveState(true, '正在实时记录...');
  pollLive();
}

async function liveStop() {
  setLiveState(false, '正在停止并生成文件...');
  const res = await fetch('/api/live-stop', {method: 'POST'});
  const data = await res.json();
  if (!data.ok) { log('ERROR: ' + data.error); setLiveState(false); return; }
  if (livePollTimer) clearTimeout(livePollTimer);
  setLiveState(false, '实时记录已完成');
  log('实时会议记录已生成:');
  for (const [kind, path] of Object.entries(data.outputs || {})) log(kind.toUpperCase() + ': ' + path);
}

async function pollLive() {
  const res = await fetch('/api/live-status');
  const data = await res.json();
  if (!data.ok) { return; }
  const captions = data.segments.map(seg => {
    const start = Math.floor(seg.start);
    const mm = String(Math.floor(start / 60)).padStart(2, '0');
    const ss = String(start % 60).padStart(2, '0');
    return '[' + mm + ':' + ss + '] ' + seg.text;
  });
  document.getElementById('liveCaptions').textContent = captions.length ? captions.join('\n') : data.log.join('\n');
  if (data.status === 'recording') {
    setLiveState(true, '正在实时记录... 已识别 ' + data.segments.length + ' 段');
    livePollTimer = setTimeout(pollLive, 1500);
  } else if (data.status === 'failed') {
    setLiveState(false, '实时记录失败');
    log('ERROR: ' + data.error);
  }
}

function watchJob(jobId) {
  currentJob = jobId;
  log('Job started: ' + jobId);
  poll();
}

async function poll() {
  if (!currentJob) return;
  const res = await fetch('/api/job/' + currentJob);
  const data = await res.json();
  document.getElementById('log').textContent = data.log.join('\n');
  if (data.status === 'running') {
    setTimeout(poll, 1000);
  } else {
    log('Status: ' + data.status);
    if (data.outputs) {
      for (const [kind, path] of Object.entries(data.outputs)) log(kind.toUpperCase() + ': ' + path);
      if (data.outputs.mp3) {
        setLastRecording(data.outputs.mp3);
        setRecordingState(false, '录制完成');
      }
    }
    if (data.error) log('ERROR: ' + data.error);
    currentJob = null;
  }
}

setRecordingState(false);
setLiveState(false);
</script>
</body>
</html>
"""


def _json(handler: BaseHTTPRequestHandler, payload: dict[str, Any], code: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _start_job(name: str, target) -> str:
    job_id = f"{int(time.time())}-{len(JOBS) + 1}"
    JOBS[job_id] = {"name": name, "status": "running", "log": [f"Job: {name}"], "outputs": None, "error": None}

    def run() -> None:
        try:
            outputs = target(lambda message: JOBS[job_id]["log"].append(message))
            JOBS[job_id]["outputs"] = {key: str(value) for key, value in (outputs or {}).items()}
            JOBS[job_id]["status"] = "done"
        except Exception as exc:
            JOBS[job_id]["error"] = str(exc)
            JOBS[job_id]["log"].append(f"ERROR: {exc}")
            JOBS[job_id]["status"] = "failed"

    threading.Thread(target=run, daemon=True).start()
    return job_id


def _language(query: dict[str, list[str]]) -> str | None:
    choice = query.get("language", ["Auto"])[0]
    return LANGUAGE_CHOICES.get(choice, None)


class Handler(BaseHTTPRequestHandler):
    server_version = "EchoScribe/0.1"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.startswith("/api/job/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = JOBS.get(job_id)
            _json(self, job if job else {"status": "missing", "log": [], "error": "job not found"}, 200)
            return
        if parsed.path == "/api/live-status":
            if LIVE_SESSION is None:
                _json(self, {"ok": True, "status": "idle", "log": [], "segments": [], "outputs": {}, "error": None})
            else:
                payload = LIVE_SESSION.snapshot()
                payload["ok"] = True
                _json(self, payload)
            return
        _json(self, {"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:
        global RECORDER, LAST_RECORDING, LIVE_SESSION
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        try:
            if parsed.path == "/api/transcribe-upload":
                raw_name = self.headers.get("X-Filename", "upload.bin")
                filename = Path(urllib.parse.unquote(raw_name)).name
                upload_dir = default_output_dir() / "uploads"
                upload_dir.mkdir(parents=True, exist_ok=True)
                media_path = upload_dir / f"{int(time.time())}-{filename}"
                remaining = int(self.headers.get("Content-Length", "0"))
                with media_path.open("wb") as fh:
                    while remaining > 0:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        fh.write(chunk)
                        remaining -= len(chunk)

                lang = _language(query)

                def target(progress):
                    return Transcriber(progress=progress).transcribe_media(media_path, default_output_dir(), language=lang)

                _json(self, {"ok": True, "job_id": _start_job(f"transcribe {filename}", target)})
                return

            if parsed.path == "/api/record-fixed":
                seconds = int(query.get("seconds", ["60"])[0])

                def target(progress):
                    global LAST_RECORDING
                    progress(f"Recording system audio for {seconds} seconds...")
                    recorder = SystemAudioRecorder(default_output_dir())
                    wav, mp3 = recorder.record_fixed(seconds)
                    LAST_RECORDING = mp3
                    progress(f"Recorded MP3: {mp3}")
                    return {"wav": wav, "mp3": mp3}

                _json(self, {"ok": True, "job_id": _start_job("record fixed duration", target)})
                return

            if parsed.path == "/api/record-start":
                RECORDER = SystemAudioRecorder(default_output_dir())
                wav = RECORDER.start()
                _json(self, {"ok": True, "wav": str(wav)})
                return

            if parsed.path == "/api/record-stop":
                if RECORDER is None:
                    raise RuntimeError("recording is not running")
                wav, mp3 = RECORDER.stop()
                LAST_RECORDING = mp3
                _json(self, {"ok": True, "wav": str(wav), "mp3": str(mp3)})
                return

            if parsed.path == "/api/transcribe-last-recording":
                if LAST_RECORDING is None:
                    raise RuntimeError("no recording is available yet")
                lang = _language(query)

                def target(progress):
                    return Transcriber(progress=progress).transcribe_media(LAST_RECORDING, default_output_dir(), language=lang)

                _json(self, {"ok": True, "job_id": _start_job("transcribe last recording", target)})
                return

            if parsed.path == "/api/live-start":
                if LIVE_SESSION is not None and LIVE_SESSION.status == "recording":
                    raise RuntimeError("live recording is already running")
                LIVE_SESSION = LiveMeetingSession(default_output_dir(), language=_language(query))
                LIVE_SESSION.start()
                _json(self, {"ok": True})
                return

            if parsed.path == "/api/live-stop":
                if LIVE_SESSION is None or LIVE_SESSION.status != "recording":
                    raise RuntimeError("live recording is not running")
                outputs = LIVE_SESSION.stop()
                _json(self, {"ok": True, "outputs": {key: str(value) for key, value in outputs.items()}})
                return

            _json(self, {"ok": False, "error": "not found"}, 404)
        except Exception as exc:
            _json(self, {"ok": False, "error": str(exc)}, 500)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    host = "127.0.0.1"
    port_env = os.environ.get("ECHOSCRIBE_PORT")
    port = int(port_env) if port_env else 0
    server = ThreadingHTTPServer((host, port), Handler)
    port = server.server_address[1]
    url = f"http://{host}:{port}/"
    print(f"{APP_NAME} is running at {url}")
    if os.environ.get("ECHOSCRIBE_NO_BROWSER") != "1":
        webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
