"""音频处理路由"""

import os
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from src.api.schemas.models import (
    SynthesizeRequest,
    SynthesizeResponse,
    VoiceTrainRequest,
    VoiceItem,
)
from src.audio.tts import TTSEngine, VOICES_DIR
from src.common.config_manager import ConfigManager
from src.common.exceptions import TTSError
from src.common.file_utils import ensure_dir
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

tts_engine = TTSEngine()
config = ConfigManager()


# ─────────────────────────────── 音色列表 ────────────────────────────────

@router.get("/voices", response_model=list[VoiceItem])
async def list_voices():
    """获取可用音色列表"""
    return tts_engine.list_voices()


# ─────────────────────────── 语音合成（双接口） ────────────────────────────

@router.post("/synthesize/path", response_model=SynthesizeResponse)
async def synthesize_path(req: SynthesizeRequest):
    """语音合成 — 返回 JSON（含服务端绝对路径），供数字人步骤使用。"""
    try:
        audio_path = await tts_engine.synthesize(req.text, req.voice_id, req.speed)
    except TTSError as e:
        raise HTTPException(status_code=503, detail=str(e))

    output_dir = config.get_output_dir()
    try:
        rel = Path(audio_path).relative_to(output_dir)
        audio_url = f"/output/{rel.as_posix()}"
    except ValueError:
        audio_url = ""

    duration = 0.0
    try:
        ffprobe = config.get_ffmpeg_path().replace("ffmpeg", "ffprobe")
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=15,
        )
        duration = float(result.stdout.strip() or 0)
    except Exception:
        pass

    return SynthesizeResponse(
        audio_path=audio_path,
        audio_url=audio_url,
        duration=duration,
    )


@router.post("/synthesize")
async def synthesize_blob(req: SynthesizeRequest):
    """语音合成 — 直接返回 WAV 二进制（供预听使用）。"""
    try:
        audio_path = await tts_engine.synthesize(req.text, req.voice_id, req.speed)
    except TTSError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return FileResponse(audio_path, media_type="audio/wav", filename="synthesized.wav")


# ─────────────────────────────── 参考音频上传 ─────────────────────────────

@router.post("/upload")
async def upload_voice_sample(file: UploadFile = File(...)):
    """上传参考音频文件，返回服务端保存路径。"""
    suffix = Path(file.filename or "audio.wav").suffix.lower()
    if suffix not in (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".webm", ".flac"):
        raise HTTPException(status_code=400, detail="仅支持 WAV/MP3/M4A/AAC/OGG/WebM/FLAC 格式")

    upload_dir = config.get_output_dir() / "upload" / "voice"
    ensure_dir(upload_dir)

    save_path = upload_dir / file.filename
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"参考音频已上传: {save_path}")
    return {"path": str(save_path), "filename": file.filename}


# ─────────────────────────────── 声音训练 ────────────────────────────────

@router.post("/train")
async def train_voice(req: VoiceTrainRequest):
    """声音训练：将参考音频注册为可用音色。

    当前实现：将参考音频复制到 resources/voices/ 目录并以名称命名，
    非 WAV 格式会通过 FFmpeg 自动转换为 WAV，确保 CosyVoice 兼容。
    后续 list_voices() 即可自动发现该音色。
    当 CosyVoice 支持在线训练 API 时，可在此处调用真实训练接口。
    """
    src = Path(req.audio_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"音频文件不存在: {req.audio_path}")

    safe_name = "".join(c for c in req.name if c.isalnum() or c in ("-", "_", " ")).strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="音色名称不合法")

    ensure_dir(VOICES_DIR)
    dest = VOICES_DIR / f"{safe_name}.wav"

    if src.suffix.lower() == ".wav":
        shutil.copy2(str(src), str(dest))
    else:
        ffmpeg_path = config.get_ffmpeg_path()
        try:
            result = subprocess.run(
                [ffmpeg_path, "-i", str(src), "-acodec", "pcm_s16le", "-y", str(dest)],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"音频格式转换失败: {result.stderr[:200]}",
                )
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="FFmpeg 未找到，请在设置中配置正确的 FFmpeg 路径",
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="音频格式转换超时")

    logger.info(f"音色已保存: {dest}")
    return {
        "status": "success",
        "message": f"音色「{safe_name}」已保存",
        "voice": {"name": safe_name, "path": str(dest)},
    }


@router.get("/voices/{voice_name}/preview")
async def preview_voice(voice_name: str):
    """预览音色的参考音频文件"""
    voices = tts_engine.list_voices()
    target = next((v for v in voices if v["name"] == voice_name), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"音色不存在: {voice_name}")

    file_path = Path(target["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="音频文件不存在")

    suffix = file_path.suffix.lower()
    media_types = {
        ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
        ".ogg": "audio/ogg", ".flac": "audio/flac", ".webm": "audio/webm",
    }
    media_type = media_types.get(suffix, "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type, filename=file_path.name)


@router.put("/voices/{voice_name}")
async def rename_voice(voice_name: str, new_name: str):
    """重命名音色"""
    voices = tts_engine.list_voices()
    target = next((v for v in voices if v["name"] == voice_name), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"音色不存在: {voice_name}")

    safe_name = "".join(c for c in new_name if c.isalnum() or c in ("-", "_", " ")).strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="新名称不合法")

    # 检查新名称是否已存在
    if any(v["name"] == safe_name for v in voices):
        raise HTTPException(status_code=409, detail=f"音色「{safe_name}」已存在")

    old_path = Path(target["path"])
    new_path = old_path.parent / f"{safe_name}{old_path.suffix}"
    old_path.rename(new_path)
    logger.info(f"音色已重命名: {voice_name} -> {safe_name}")
    return {"status": "success", "message": f"音色已重命名为「{safe_name}」"}


@router.delete("/voices/{voice_name}")
async def delete_voice(voice_name: str):
    """删除指定音色文件"""
    voices = tts_engine.list_voices()
    target = next((v for v in voices if v["name"] == voice_name), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"音色不存在: {voice_name}")

    Path(target["path"]).unlink(missing_ok=True)
    logger.info(f"音色已删除: {voice_name}")
    return {"status": "success", "message": f"音色「{voice_name}」已删除"}


# ─────────────────────────────── 服务状态 ────────────────────────────────

@router.get("/service/status")
async def tts_service_status():
    """检查 CosyVoice 服务状态"""
    online = await tts_engine.check_service()
    return {"status": "online" if online else "offline"}
