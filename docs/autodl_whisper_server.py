"""
AutoDL 云端 Whisper ASR 服务
============================
部署说明：
  1. 将此文件上传到 AutoDL 实例（或直接在 JupyterLab 中创建）
  2. 在 AutoDL 实例终端执行：
       pip install openai-whisper fastapi uvicorn python-multipart
       python autodl_whisper_server.py
  3. AutoDL 控制台 → 自定义服务 → 获取公网访问地址（端口 6006）
  4. 将该地址填入 AvatarAgent 的 config.ini [cloud_gpu] 配置节

API 端点（与 AvatarAgent ASREngine 兼容）：
  POST /asr/transcribe        — 普通转录，返回 { "text": "..." }
  POST /asr/transcribe/ts     — 带时间戳转录，返回 { "segments": [...] }
  GET  /health                — 健康检查
"""

import io
import os
import tempfile
from pathlib import Path
from typing import Optional

import uvicorn
import whisper
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# ── 配置 ──────────────────────────────────────────────────────────────────────
MODEL_SIZE = os.getenv("WHISPER_MODEL", "turbo")   # 可通过环境变量覆盖
PORT = int(os.getenv("PORT", "6006"))               # AutoDL 对外暴露端口固定为 6006
API_KEY = os.getenv("WHISPER_API_KEY", "")          # 可选：设置访问密钥

# ── 全局模型（启动时加载一次，后续复用）────────────────────────────────────────
print(f"[startup] 正在加载 Whisper {MODEL_SIZE} 模型...")
_model = whisper.load_model(MODEL_SIZE)
print(f"[startup] Whisper {MODEL_SIZE} 模型加载完毕 ✅")

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(title="AvatarAgent Whisper ASR Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _verify_api_key(authorization: Optional[str]):
    """验证 API Key（可选）"""
    if not API_KEY:
        return  # 未设置则跳过验证
    if not authorization or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API Key")


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_SIZE}


@app.post("/asr/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("zh"),
    model: str = Form(MODEL_SIZE),
    authorization: Optional[str] = None,
):
    """
    普通转录接口（与 AvatarAgent ASREngine._transcribe_remote 兼容）
    返回：{ "text": "识别到的文本" }
    """
    _verify_api_key(authorization)

    # 保存上传文件到临时目录
    suffix = Path(file.filename).suffix if file.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = _model.transcribe(tmp_path, language=language, fp16=True)
        text = result["text"].strip()
        print(f"[transcribe] 完成，文本长度: {len(text)}")
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/asr/transcribe/timestamps")
async def transcribe_with_timestamps(
    file: UploadFile = File(...),
    language: str = Form("zh"),
    model: str = Form(MODEL_SIZE),
    timestamps: str = Form("true"),
    authorization: Optional[str] = None,
):
    """
    带时间戳转录接口（与 AvatarAgent ASREngine._transcribe_remote_with_timestamps 兼容）
    返回：{ "segments": [{"start": 0.0, "end": 2.5, "text": "你好"}, ...] }
    """
    _verify_api_key(authorization)

    suffix = Path(file.filename).suffix if file.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = _model.transcribe(tmp_path, language=language, fp16=True)
        segments = [
            {
                "start": round(seg["start"], 3),
                "end": round(seg["end"], 3),
                "text": seg["text"].strip(),
            }
            for seg in result.get("segments", [])
        ]
        print(f"[transcribe_ts] 完成，共 {len(segments)} 段")
        return {"segments": segments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    print(f"[startup] 启动 Whisper API 服务，端口: {PORT}")
    print(f"[startup] 访问地址: http://0.0.0.0:{PORT}")
    print(f"[startup] 健康检查: http://0.0.0.0:{PORT}/health")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
