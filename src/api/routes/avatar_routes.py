"""数字人路由"""

from fastapi import APIRouter

from src.api.schemas.models import AvatarGenerateRequest, AvatarModel, StatusResponse
from src.avatar.heygem import HeyGemEngine, TuiliONNXEngine
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


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


@router.post("/generate")
async def generate_avatar(req: AvatarGenerateRequest):
    """生成数字人视频"""
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
