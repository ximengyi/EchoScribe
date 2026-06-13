# EchoScribe 更新日志

## v1.1

EchoScribe 1.1 重点优化了桌面 Web UI、录音转写工作流和中文转写结果。

### 新增

- 三端自动构建发布：推送 `v*` 标签后自动构建 Windows、Linux、macOS 便携包。
- 三个主功能统一为 Tab 页面：
  - 导入音频 / 视频转写
  - 录制电脑声音
  - 实时会议记录
- 每个 Tab 增加“打开输出目录”按钮，方便查看生成的 TXT、SRT、JSON、音频文件。
- 录制电脑声音页增加录音文件路径展示，录制完成后可直接点击“转写此录音”。
- 页面增加“退出 EchoScribe”按钮。
- 浏览器页面关闭后，后台进程会自动退出，避免残留多个 `EchoScribe.exe`。
- 中文转写结果默认转换为简体中文。

### 优化

- 录制电脑声音页面按钮重新分组，避免按钮和长路径挤在一起。
- “定时长录制”按钮改为更明确的“开始定时录制”。
- 录制状态增加明显提示和计时显示。
- 转写输出同时包含：
  - 带时间戳文本：`.transcript.txt`
  - 无时间戳正文：`.transcript.plain.txt`
  - 字幕文件：`.transcript.srt`
  - 结构化数据：`.transcript.json`

### 修复

- 修复打包后缺少 faster-whisper VAD 模型资源导致转写失败的问题。
- 修复关闭浏览器页面后本地服务进程不退出的问题。
- 修复中文转写结果可能输出繁体的问题。

### 下载文件

Release 页面会提供以下三个便携包：

- `EchoScribe-windows-x64.zip`
- `EchoScribe-linux-x64.zip`
- `EchoScribe-macos-arm64.zip`
