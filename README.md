# AvatarAgent

> AI 数字人口播视频自动化生成工具

本地运行、模块化、可扩展的数字人口播视频全流程自动化系统。

## 功能

- ✅ 提取对标视频口播文案
- ✅ AI 文案仿写与改写 (Deepseek API)
- ✅ 语音克隆 & TTS 合成 (CosyVoice)
- ✅ 数字人口播视频生成 (HeyGem + TuiliONNX 双引擎)
- ✅ 自动生成字幕 (FFmpeg)
- ✅ 背景音乐管理 (FFmpeg)
- ✅ 视频封面生成 (FFmpeg + Pillow)
- ✅ 多平台发布 (抖音/小红书/视频号)
- ✅ 一键全流程执行

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python 3.10+ / FastAPI |
| 前端 | Vue 3 + TypeScript (前后端分离) |
| 语音识别 | Whisper |
| 语音合成 | CosyVoice |
| 数字人 | HeyGem / TuiliONNX |
| 视频处理 | FFmpeg |
| AI 文案 | Deepseek API |
| 发布 | Playwright |

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
uv venv
.venv\Scripts\activate    # Windows

# 安装依赖
uv pip install -e .
```

### 2. 配置

编辑 `config/config.ini`，设置：
- Deepseek API Key
- CosyVoice / HeyGem / TuiliONNX 服务地址
- FFmpeg 路径
- Chrome 浏览器路径

### 3. 启动

```bash
python launcher.py
```

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 项目结构

```
AvatarAgent/
├── config/           # 配置文件
├── src/
│   ├── common/       # 公共工具
│   ├── script/       # 文案处理
│   ├── audio/        # 音频处理
│   ├── avatar/       # 数字人驱动
│   ├── video/        # 视频后期
│   ├── uploader/     # 平台发布
│   ├── pipeline/     # 流水线编排
│   └── api/          # FastAPI 接口
├── resources/        # 资源文件
├── output/           # 输出目录
├── launcher.py       # 启动器
└── pyproject.toml    # 项目配置
```

## API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/script/extract` | 提取视频文案 |
| POST | `/api/script/rewrite` | 文案仿写 |
| POST | `/api/script/description` | 生成视频描述 |
| GET | `/api/audio/voices` | 音色列表 |
| POST | `/api/audio/synthesize` | 语音合成 |
| GET | `/api/avatar/models` | 数字人模型 |
| POST | `/api/avatar/generate` | 生成数字人视频 |
| POST | `/api/video/subtitle` | 字幕处理 |
| POST | `/api/video/bgm/add` | 添加 BGM |
| POST | `/api/video/cover` | 生成封面 |
| POST | `/api/upload/douyin` | 发布抖音 |
| POST | `/api/upload/xiaohongshu` | 发布小红书 |
| POST | `/api/upload/shipinhao` | 发布视频号 |
| POST | `/api/upload/all` | 全平台发布 |
| POST | `/api/pipeline/run` | 一键全流程 |
| GET | `/api/config/services` | 服务状态 |
