# EchoScribe 离线音视频转文字工具

EchoScribe 是一个 Windows 本地离线转写工具，用来把音频、视频或电脑正在播放的声音转换成文字。软件内置 `faster-whisper small` 模型和 `ffmpeg`，转写过程在本机完成，不会把音频上传到外部服务。

## 主要功能

- 导入本地音频或视频文件并转写成文字。
- 录制电脑当前播放的系统声音。
- 实时会议记录：同时录制电脑扬声器和麦克风，并在网页中滚动显示实时字幕片段。
- 支持自动识别语言、中文、英文。
- 每次转写默认生成 4 种结果文件：
  - `.transcript.txt`：带时间戳的文字稿。
  - `.transcript.plain.txt`：不带时间戳的纯文字稿。
  - `.transcript.srt`：字幕文件。
  - `.transcript.json`：包含时间戳和分段信息的结构化数据。
- 内置 `ffmpeg.exe`，可自动抽取视频中的音频并转码。

第一版不支持直接下载抖音、B站、YouTube 等平台链接。你可以先把视频保存到本地再导入，或者播放视频时使用“录制电脑声音”。

## 便携版使用方法

1. 解压 `EchoScribe-portable-web-fixed.zip`。
2. 进入解压后的 `EchoScribe` 文件夹。
3. 双击 `EchoScribe.exe`。
4. 程序会自动打开浏览器中的本地界面。
5. 选择语言：`Auto`、`Chinese` 或 `English`。
6. 导入音频/视频文件，点击“上传并转写”。
7. 或者点击“开始录制”录制电脑声音，停止后点击“转写最后一次录音”。
8. 如果要记录会议或直播讨论，使用“实时会议记录”：
   - 点击“开始实时记录”。
   - 网页会显示红色录制状态，并滚动显示实时字幕。
   - 点击“停止并生成文件”后，会自动保存麦克风音频、系统声音音频、混合音频和文字记录。

所有结果默认保存在程序目录下的 `outputs` 文件夹。

## 开发模式运行

如果你想从源码运行：

```powershell
cd D:\pywork\EchoScribe
.\scripts\setup_dev.ps1
.\.venv\Scripts\python.exe -m echoscribe.app_web
```

## 打包便携版

```powershell
cd D:\pywork\EchoScribe
.\scripts\build_portable.ps1
```

打包完成后会生成：

```text
dist\EchoScribe-portable.zip
```

## 推荐硬件配置

最低配置：

- Windows 10 或 Windows 11
- 4 核 CPU
- 8 GB 内存
- 2 GB 可用磁盘空间

推荐配置：

- 6 核或更高 CPU
- 16 GB 内存
- SSD
- 4 GB 以上可用磁盘空间

第一版默认使用 CPU 进行 `int8` 推理。以后可以继续增加 NVIDIA GPU 加速支持。

## 注意事项

- 内置的 `small` 模型支持中文、英文和自动语言识别。
- 专业术语、股票术语、医学术语、法律术语等可能需要人工校对。
- 录制电脑声音时，系统提示音、其它播放器声音也会被一起录进去。
- 实时会议记录中，实时字幕按麦克风短片段生成；停止后会同时保存系统声音、麦克风和混合音频。
- 默认麦克风设备名为 `麦克风 (Realtek High Definition Audio)`。如果你的电脑设备名不同，可以后续在设置里扩展选择功能。
- 音频质量越好，转写结果越准确。
- 第一次转写时模型加载会稍慢，后续会快一些。
