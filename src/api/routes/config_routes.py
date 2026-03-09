"""Configuration APIs."""

from __future__ import annotations

from typing import Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from src.api.schemas.models import ApiKeyRequest
from src.common.config_manager import ConfigManager
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

config = ConfigManager()


@router.get("/apikeys")
async def get_api_keys():
    return {"keys": config.get_api_keys()}


@router.post("/apikeys")
async def add_api_key(req: ApiKeyRequest):
    keys = config.add_api_key(req.key)
    return {"status": "success", "keys": keys}


@router.delete("/apikeys")
async def delete_api_key(req: ApiKeyRequest):
    keys = config.remove_api_key(req.key)
    return {"status": "success", "keys": keys}


@router.get("/services")
async def check_services():
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


class CloudGpuConfig(BaseModel):
    enabled: bool
    api_url: Optional[str] = ""
    api_key: Optional[str] = ""


@router.get("/cloud-gpu")
async def get_cloud_gpu():
    return {
        "enabled": config.is_cloud_gpu_enabled(),
        **config.get_cloud_gpu_config(),
    }


@router.post("/cloud-gpu")
async def set_cloud_gpu(req: CloudGpuConfig):
    config.set("cloud_gpu", "enabled", "true" if req.enabled else "false")
    config.set("cloud_gpu", "api_url", req.api_url or "")
    config.set("cloud_gpu", "api_key", req.api_key or "")
    config.reload()
    return {
        "status": "success",
        "enabled": req.enabled,
        "api_url": req.api_url,
    }


@router.post("/cloud-gpu/test")
async def test_cloud_gpu():
    cloud_cfg = config.get_cloud_gpu_config()
    api_url = cloud_cfg.get("api_url", "")
    api_key = cloud_cfg.get("api_key", "")

    if not api_url:
        return {"status": "error", "message": "API URL is empty."}

    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{api_url}/health", headers=headers)
            response.raise_for_status()
            data = response.json()
        return {"status": "online", "model": data.get("model", "unknown")}
    except httpx.ConnectError:
        return {"status": "error", "message": "Cannot connect to cloud GPU endpoint."}
    except httpx.TimeoutException:
        return {"status": "error", "message": "Cloud GPU endpoint timed out."}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


class WhisperConfig(BaseModel):
    model_size: Optional[str] = None
    device: Optional[str] = None


@router.get("/local-asr")
async def get_local_asr():
    from src.audio.asr import get_local_asr_status

    status = get_local_asr_status()
    status["model_size"] = config.get("whisper", "model_size", "turbo")
    status["whisper_device"] = config.get_whisper_device()
    return status


@router.post("/local-asr")
async def set_whisper_config(req: WhisperConfig):
    if req.model_size is not None:
        valid_sizes = {"tiny", "base", "small", "medium", "large", "turbo"}
        if req.model_size not in valid_sizes:
            return {"status": "error", "message": f"Unsupported model size: {req.model_size}"}
        config.set("whisper", "model_size", req.model_size)

    if req.device is not None:
        valid_devices = {"auto", "cuda", "cpu"}
        if req.device not in valid_devices:
            return {"status": "error", "message": f"device 必须是 auto、cuda 或 cpu"}
        config.set("whisper", "device", req.device)

    config.reload()
    return {
        "status": "success",
        "model_size": config.get("whisper", "model_size", "turbo"),
        "device": config.get_whisper_device(),
    }


class CosyVoiceRuntimeConfig(BaseModel):
    device: str


@router.get("/cosyvoice-runtime")
async def get_cosyvoice_runtime():
    from src.audio.cosyvoice_deploy import get_cosyvoice_runtime_status

    status = get_cosyvoice_runtime_status()
    status["device"] = config.get_cosyvoice_device()
    status["model_dir"] = config.get_cosyvoice_model_dir()
    return status


@router.post("/cosyvoice-runtime")
async def set_cosyvoice_runtime(req: CosyVoiceRuntimeConfig):
    device = (req.device or "").strip().lower()
    if device not in {"gpu", "cpu"}:
        return {"status": "error", "message": "device 必须是 gpu 或 cpu"}

    config.set("cosyvoice", "device", device)
    config.reload()
    return {
        "status": "success",
        "device": device,
        "message": "CosyVoice 运行设置已保存，重启服务后生效。",
    }
