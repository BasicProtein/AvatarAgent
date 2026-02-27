"""配置管理路由"""

from fastapi import APIRouter

from src.api.schemas.models import ApiKeyRequest
from src.common.config_manager import ConfigManager
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

config = ConfigManager()


@router.get("/apikeys")
async def get_api_keys():
    """获取 API Key 列表"""
    return {"keys": config.get_api_keys()}


@router.post("/apikeys")
async def add_api_key(req: ApiKeyRequest):
    """保存 API Key"""
    keys = config.add_api_key(req.key)
    return {"status": "success", "keys": keys}


@router.delete("/apikeys")
async def delete_api_key(req: ApiKeyRequest):
    """删除 API Key"""
    keys = config.remove_api_key(req.key)
    return {"status": "success", "keys": keys}


@router.get("/services")
async def check_services():
    """检查所有外部服务状态"""
    from src.audio.tts import TTSEngine
    from src.avatar.heygem import HeyGemEngine, TuiliONNXEngine

    tts = TTSEngine()
    heygem = HeyGemEngine()
    tuilionnx = TuiliONNXEngine()

    return {
        "cosyvoice": "online" if await tts.check_service() else "offline",
        "heygem": "online" if await heygem.check_service() else "offline",
        "tuilionnx": "online" if await tuilionnx.check_service() else "offline",
    }
