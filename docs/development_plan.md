# AvatarAgent 开发计划
> 制定时间：2026-03-03 | 基于 Context7 文档研究 + 现有代码分析

---

## 一、当前状态速览

| 模块 | 状态 | 说明 |
|------|------|------|
| 文案提取（yt-dlp） | ⚠️ 代码完备，**yt-dlp 未安装** | 命令行调用，需安装到环境 |
| 语音识别（Whisper） | ⚠️ 代码完备，**whisper 未安装** | `import whisper` 会 ImportError |
| 文案仿写（Deepseek） | ✅ 已接入 | API Key 已配置 |
| 语音合成（CosyVoice） | ❌ **服务离线** | 需要单独部署 Docker/gRPC 服务 |
| 数字人生成（HeyGem） | ❌ **服务离线** | 需要 Docker Compose 启动 |
| 声音训练（注册音色） | ✅ 可用 | 文件复制注册，无需外部服务 |
| 形象保存 | ✅ 可用 | 文件复制注册，无需外部服务 |
| 字幕/BGM/封面 | ✅ FFmpeg 本地可用 | - |
| 平台发布 | ✅ Playwright 已接入 | - |

---

## 二、分阶段开发计划

### 🟢 P0 阶段：立即可完成（无需外部服务）

**目标**：让现有功能完整跑通，让用户可以实际体验完整产品

---

#### P0-1：安装 yt-dlp + Whisper，打通文案提取

**问题根因**：
- `yt-dlp` 需要在 Python 环境中安装（`pip install yt-dlp`）
- `whisper` 需要安装 OpenAI Whisper（`pip install openai-whisper`）
- 当前代码已调用 `subprocess yt-dlp` 和 `import whisper`，逻辑完整，只缺依赖

**安装指令**：
```bash
uv add yt-dlp
uv add openai-whisper
```

**Whisper 模型选取**（权衡速度/精度）：

| 模型 | 大小 | 中文效果 | 速度 |
|------|------|------|----|
| `tiny` | 75MB | 一般 | 极快 |
| `base` | 145MB | 较好 | 快 |
| `small` | 466MB | 好 | 中 |
| `medium` | 1.5GB | 很好 | 慢 |
| `turbo` | 809MB | 很好 | 快（**推荐**）|

**推荐**：`turbo` 模型（OpenAI 最新，速度快且精度高）

**改动**：`src/audio/asr.py` 中 `load_model` 调用，确认使用 `"turbo"`

---

#### P0-2：改进文案提取的抖音短链支持

**现状**：yt-dlp 本身支持抖音，但抖音有防爬机制

**方案**：在 `_download_audio` 中增加 Cookie 和 Headers 配置：

```python
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
    'outtmpl': output_path,
    'quiet': True,
    'no_warnings': True,
    # 抖音防反爬
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.douyin.com/',
    },
}
```

---

#### P0-3：前端服务状态面板完善

**目标**：在首页或设置页清晰展示各服务状态，引导用户按需启动

**设计原则**（参考 `ui_style_guide.md`）：
- 状态卡片：`border-radius: 12px`，`border: 1px solid rgba(31,30,29,0.08)`
- 已连接：绿色小圆点 `#27AE60` + 文字"已连接"
- 离线：暗红色小圆点 + 文字"未启动" + 快捷部署引导按钮

---

### 🟡 P1 阶段：部署 CosyVoice（语音合成）

**CosyVoice 部署方式（按复杂度从低到高）**：

#### 方式 A：FastAPI Docker（推荐，最快）
```bash
docker pull guiji2025/cosyvoice
# 或官方：
docker build -t cosyvoice:v1.0 .  # 在 CosyVoice/runtime/python 目录
docker run -d --runtime=nvidia \
  -p 50000:50000 cosyvoice:v1.0 \
  /bin/bash -c "cd /opt/CosyVoice/runtime/python/fastapi && python3 server.py --port 50000 --model_dir iic/CosyVoice-300M"
```

#### 方式 B：本地安装运行
```bash
git clone https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
conda create -n cosyvoice python=3.10
pip install -r requirements.txt
python api_server.py --port 50000
```

**Key API（已在 `src/audio/tts.py` 使用）**：
- `POST /inference_zero_shot` — 零样本克隆（用于注册音色后合成）
- `POST /inference_sft` — 预训练音色合成

**CosyVoice 核心 API 示例**：
```python
# Zero-shot voice cloning
cosyvoice.inference_zero_shot(
    tts_text='你好，这是克隆的声音',
    prompt_text='原始参考文本',   # 参考音频的文字
    prompt_speech_16k=prompt_audio,  # 3-30秒参考音频
)
```

**后端 `config.ini` 中的配置项**：
```ini
[cosyvoice]
host = 127.0.0.1
port = 50000
```

---

### 🟡 P1 阶段：部署 HeyGem（数字人生成）

**HeyGem 由三个 Docker 服务组成**：

```bash
# 拉取镜像
docker pull guiji2025/fun-asr        # ASR 服务（声音训练）
docker pull guiji2025/fish-speech-ziming  # TTS 服务
docker pull guiji2025/heygem.ai      # 视频生成

# 或用 lite 版（仅视频合成，不含完整 ASR+TTS）
docker-compose -f docker-compose-lite.yml up -d
```

**HeyGem API 调用流程**（已在代码中实现）：

```
1. 声音训练（可选，已有声音则跳过）
POST /v1/preprocess_and_tran
{
  "format": ".wav",
  "reference_audio": "音频路径.wav",
  "lang": "zh"
}
→ 返回: { "asr_format_audio_url": "xxx.wav", "reference_audio_text": "xxx" }

2. 音频合成
POST /v1/tts
{
  "speaker": "{uuid}",
  "text": "要合成的文本",
  "reference_audio": "{asr_format_audio_url}",
  "reference_text": "{reference_audio_text}",
  ...
}

3. 视频合成
POST /v1/inference
{
  "audio_url": "合成音频路径",
  "video_url": "数字人视频路径",
  "code": "{uuid}",
  "chaofen": 0,
  "watermark_switch": 0,
  "pn": 1
}
```

---

### 🔵 P2 阶段：产品体验打磨

#### P2-1：文案提取进度反馈
yt-dlp 下载可能需要 10-60 秒，Whisper 转录也需时间，需要实时进度显示。

**方案**：使用 SSE（Server-Sent Events）推送进度：
```python
# FastAPI SSE 端点
@router.get("/extract/stream")
async def extract_stream(video_url: str):
    async def generator():
        yield f"data: {json.dumps({'step': 'downloading', 'progress': 0})}\n\n"
        # ... 下载
        yield f"data: {json.dumps({'step': 'transcribing', 'progress': 50})}\n\n"
        # ... 转录
        yield f"data: {json.dumps({'step': 'done', 'text': result, 'progress': 100})}\n\n"
    return EventSourceResponse(generator())
```

**前端**：替换现在的 loading 按钮为带进度条的状态面板

#### P2-2：Whisper 模型预加载
当前每次提取都重新加载模型（约 3-10 秒），应改为启动时加载一次：

```python
# src/audio/asr.py
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("turbo")
    return _whisper_model
```

#### P2-3：声音训练体验优化
当前"注册音色"是文件复制，实际应支持：
1. 预览克隆音质（用克隆声音说一句测试文本）
2. 音色列表显示波形缩略图
3. 删除音色时同步删除文件

#### P2-4：数字人生成任务队列
视频生成是重计算任务（HeyGem 每分钟视频约需 2-5 分钟），需要：
- 后台 celery 或 asyncio 任务队列
- 前端任务状态轮询
- 任务历史记录页面

---

## 三、立即可执行的安装步骤

```bash
# 1. 安装 yt-dlp（视频下载）
uv add yt-dlp

# 2. 安装 openai-whisper（语音识别）
# 注意：需要先安装 ffmpeg（已有），以及 torch
uv add openai-whisper

# 3. 验证安装
python -c "import yt_dlp; print('yt-dlp OK')"
python -c "import whisper; print('whisper OK')"
```

> ⚠️ Whisper 首次加载 `turbo` 模型时会自动从网络下载（约 809MB）

---

## 四、开发优先级总表

| 优先级 | 任务 | 工作量 | 依赖 |
|--------|------|--------|------|
| P0 | 安装 yt-dlp + whisper | 0.5h | 无 |
| P0 | 调整 Whisper 模型为 turbo | 0.5h | 无 |
| P0 | 抖音短链 Cookie 支持 | 1h | yt-dlp |
| P0 | 首页服务状态面板 UI | 2h | 无 |
| P1 | 部署 CosyVoice Docker | 2h（含配置）| GPU/Docker |
| P1 | 部署 HeyGem Docker | 2h（含配置）| GPU/Docker |
| P1 | 验证完整流水线 | 2h | 上两项 |
| P2 | 文案提取 SSE 进度 | 3h | yt-dlp+whisper |
| P2 | Whisper 模型预加载 | 1h | whisper |
| P2 | 数字人任务队列 | 4h | HeyGem |
| P2 | 声音训练质量预览 | 2h | CosyVoice |

---

## 五、UI 设计规范引用

> 所有新 UI 开发必须遵循 `docs/ui_style_guide.md`

**关键设计原则（摘要）**：
- 按钮圆角：`10px`（非 `9999px`）
- 边框：`1px solid rgba(31,30,29,0.12)`（实线，半透明）
- 背景：`rgba(250,249,245,0.6)`（温暖象牙白）
- 按钮字重：500（Medium）
- Primary 按钮：黑底白字 `#141413 / #fff`
- 状态颜色：成功 `#27AE60`，错误 `#C0392B`，警告 `#E67E22`

**服务状态指示器组件设计**：
```
┌─────────────────────────────────────┐
│  ● yt-dlp        已安装    v2025.x   │  ← 绿点
│  ● Whisper       已安装    turbo     │  ← 绿点
│  ● CosyVoice     未启动              │  ← 红点 + [部署指南]
│  ● HeyGem        未启动              │  ← 红点 + [部署指南]
└─────────────────────────────────────┘
```

---

## 六、HeyGem vs CosyVoice 架构关系

```
用户上传参考音频
       │
       ▼
  [HeyGem] 声音训练 → asr_format_audio_url + reference_audio_text
       │
       ▼
  [HeyGem] 文本转音频 → 合成 WAV
  OR
  [CosyVoice] 零样本克隆 → 合成 WAV（更自然）
       │
       ▼
  [HeyGem] 视频生成 (audio_url + video_url) → 数字人 MP4
```

> CosyVoice 负责更高质量的 TTS；HeyGem 的视频合成引擎不依赖 CosyVoice，可以单独使用。
