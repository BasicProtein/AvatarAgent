"""配置管理路由"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

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


# ─────────────────────────── 云端 GPU 配置 ────────────────────────────────────

class CloudGpuConfig(BaseModel):
    enabled: bool
    api_url: Optional[str] = ""
    api_key: Optional[str] = ""


@router.get("/cloud-gpu")
async def get_cloud_gpu():
    """获取云端 GPU 配置"""
    return {
        "enabled": config.is_cloud_gpu_enabled(),
        **config.get_cloud_gpu_config(),
    }


@router.post("/cloud-gpu")
async def set_cloud_gpu(req: CloudGpuConfig):
    """保存云端 GPU 配置"""
    config.set("cloud_gpu", "enabled", "true" if req.enabled else "false")
    config.set("cloud_gpu", "api_url", req.api_url or "")
    config.set("cloud_gpu", "api_key", req.api_key or "")
    # 重载单例配置使其立即生效
    config.reload()
    return {
        "status": "success",
        "enabled": req.enabled,
        "api_url": req.api_url,
    }


@router.post("/cloud-gpu/test")
async def test_cloud_gpu():
    """测试云端 GPU 连接是否可用"""
    import httpx
    cloud_cfg = config.get_cloud_gpu_config()
    api_url = cloud_cfg.get("api_url", "")
    api_key = cloud_cfg.get("api_key", "")

    if not api_url:
        return {"status": "error", "message": "API 地址未配置"}

    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{api_url}/health", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return {"status": "online", "model": data.get("model", "unknown")}
    except httpx.ConnectError:
        return {"status": "error", "message": "无法连接到云端服务，请检查 SSH 隧道是否已启动"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "连接超时（10s），服务可能仍在加载"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─────────────────────────── 本地 ASR 配置 ────────────────────────────────────

class WhisperConfig(BaseModel):
    model_size: str  # tiny / base / small / medium / large / turbo


@router.get("/local-asr")
async def get_local_asr():
    """获取本地 ASR（Whisper）环境状态及当前配置"""
    from src.audio.asr import get_local_asr_status
    status = get_local_asr_status()
    status["model_size"] = config.get("whisper", "model_size", "turbo")
    return status


@router.post("/local-asr")
async def set_whisper_config(req: WhisperConfig):
    """保存 Whisper 模型大小配置"""
    valid_sizes = {"tiny", "base", "small", "medium", "large", "turbo"}
    if req.model_size not in valid_sizes:
        return {"status": "error", "message": f"无效模型大小，可选: {valid_sizes}"}
    config.set("whisper", "model_size", req.model_size)
    config.reload()
    return {"status": "success", "model_size": req.model_size}
