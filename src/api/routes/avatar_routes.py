"""数字人路由"""

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas.models import (
    AvatarGenerateRequest,
    AvatarSaveRequest,
    AvatarModel,
    StatusResponse,
)
from src.avatar.heygem import HeyGemEngine, TuiliONNXEngine, MODELS_DIR
from src.common.config_manager import ConfigManager
from src.common.exceptions import AvatarGenerateError
from src.common.file_utils import ensure_dir
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
config = ConfigManager()

# 形象元数据文件
AVATARS_META = MODELS_DIR / "avatars_meta.json"


def _load_avatars_meta() -> list[dict]:
    """读取已保存形象元数据列表"""
    if AVATARS_META.exists():
        try:
            return json.loads(AVATARS_META.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_avatars_meta(data: list[dict]) -> None:
    ensure_dir(MODELS_DIR)
    AVATARS_META.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────── 模型/形象列表 ────────────────────────────

@router.get("/models", response_model=list[AvatarModel])
async def list_models():
    """获取 HeyGem 可用模型列表"""
    engine = HeyGemEngine()
    return engine.list_models()


@router.get("/faces")
async def list_faces():
    """获取 TuiliONNX 可用人物列表"""
    engine = TuiliONNXEngine()
    return engine.list_faces()


@router.get("/saved")
async def list_saved_avatars():
    """获取已保存的自定义形象列表"""
    return _load_avatars_meta()


# ─────────────────────────── 视频文件上传 ────────────────────────────────

@router.post("/upload")
async def upload_avatar_video(file: UploadFile = File(...)):
    """上传人脸视频文件，返回服务端保存路径，供后续「保存形象」使用。"""
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if suffix not in (".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"):
        raise HTTPException(status_code=400, detail="仅支持 MP4/AVI/MOV/WMV/FLV/MKV/WEBM 格式")

    upload_dir = config.get_output_dir() / "upload" / "avatar"
    ensure_dir(upload_dir)

    save_path = upload_dir / (file.filename or "avatar.mp4")
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"形象视频已上传: {save_path}")
    return {"path": str(save_path), "filename": file.filename}


# ─────────────────────────────── 形象保存 ────────────────────────────────

@router.post("/save")
async def save_avatar(req: AvatarSaveRequest):
    """保存自定义形象：将视频注册为数字人模型。

    将上传的人脸视频复制到 resources/models/<name>/ 目录，
    并记录到 avatars_meta.json，供后续列表显示和生成时引用。
    """
    src = Path(req.video_path)
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"视频文件不存在: {req.video_path}")

    safe_name = "".join(c for c in req.name if c.isalnum() or c in ("-", "_", " ")).strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="形象名称不合法")

    # 保存到 models 目录
    dest_dir = MODELS_DIR / safe_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / src.name
    shutil.copy2(str(src), str(dest_file))

    # 更新元数据
    avatars = _load_avatars_meta()
    # 如果已存在同名则更新
    avatars = [a for a in avatars if a.get("name") != safe_name]
    avatars.append({
        "name": safe_name,
        "description": req.description,
        "video_path": str(dest_file),
        "model_dir": str(dest_dir),
    })
    _save_avatars_meta(avatars)

    logger.info(f"形象「{safe_name}」已保存: {dest_dir}")
    return {
        "status": "success",
        "message": f"形象「{safe_name}」已保存",
        "avatar": {
            "name": safe_name,
            "description": req.description,
            "video_path": str(dest_file),
        },
    }


@router.delete("/saved/{avatar_name}")
async def delete_avatar(avatar_name: str):
    """删除已保存的自定义形象"""
    avatars = _load_avatars_meta()
    target = next((a for a in avatars if a.get("name") == avatar_name), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"形象不存在: {avatar_name}")

    # 删除目录
    dest_dir = Path(target.get("model_dir", ""))
    if dest_dir.exists():
        shutil.rmtree(str(dest_dir), ignore_errors=True)

    avatars = [a for a in avatars if a.get("name") != avatar_name]
    _save_avatars_meta(avatars)
    return {"status": "success", "message": f"形象「{avatar_name}」已删除"}


# ─────────────────────────────── 视频生成 ────────────────────────────────

@router.post("/generate")
async def generate_avatar(req: AvatarGenerateRequest):
    """生成数字人视频（同步，等待完成后返回）"""
    if req.engine == "heygem":
        engine = HeyGemEngine()
        result = await engine.generate(
            model_name=req.model_name,
            audio_path=req.audio_path,
            add_watermark=req.add_watermark,
        )
    else:
        engine = TuiliONNXEngine()
        result = await engine.generate(
            face_id=req.model_name,
            audio_path=req.audio_path,
            batch_size=req.batch_size,
            sync_offset=req.sync_offset,
            scale_h=req.scale_h,
            scale_w=req.scale_w,
            compress_inference=req.compress_inference,
            beautify_teeth=req.beautify_teeth,
            add_watermark=req.add_watermark,
        )
    return result


@router.post("/generate/stream")
async def generate_avatar_stream(req: AvatarGenerateRequest):
    """生成数字人视频 — SSE 流式返回进度日志 + 最终结果。

    事件格式：
      data: {"type": "log", "message": "..."}
      data: {"type": "result", "video_path": "..."}
      data: {"type": "error", "message": "..."}
    """
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def on_progress(msg: str) -> None:
        queue.put_nowait(json.dumps({"type": "log", "message": msg}, ensure_ascii=False))

    async def run_generation() -> None:
        try:
            if req.engine == "heygem":
                engine = HeyGemEngine()
                result = await engine.generate(
                    model_name=req.model_name,
                    audio_path=req.audio_path,
                    add_watermark=req.add_watermark,
                    on_progress=on_progress,
                )
            else:
                engine = TuiliONNXEngine()
                result = await engine.generate(
                    face_id=req.model_name,
                    audio_path=req.audio_path,
                    batch_size=req.batch_size,
                    sync_offset=req.sync_offset,
                    scale_h=req.scale_h,
                    scale_w=req.scale_w,
                    compress_inference=req.compress_inference,
                    beautify_teeth=req.beautify_teeth,
                    add_watermark=req.add_watermark,
                )
            queue.put_nowait(json.dumps(
                {"type": "result", **result},
                ensure_ascii=False,
            ))
        except AvatarGenerateError as e:
            queue.put_nowait(json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False))
        except Exception as e:
            queue.put_nowait(json.dumps({"type": "error", "message": f"生成失败: {e}"}, ensure_ascii=False))
        finally:
            queue.put_nowait(None)

    async def event_generator():
        task = asyncio.create_task(run_generation())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {item}\n\n"
        finally:
            task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─────────────────────────────── 服务状态 ────────────────────────────────

@router.get("/service/heygem/status")
async def heygem_status():
    """检查 HeyGem 服务状态"""
    engine = HeyGemEngine()
    online = await engine.check_service()
    return {"status": "online" if online else "offline"}


@router.get("/service/tuilionnx/status")
async def tuilionnx_status():
    """检查 TuiliONNX 服务状态"""
    engine = TuiliONNXEngine()
    online = await engine.check_service()
    return {"status": "online" if online else "offline"}
