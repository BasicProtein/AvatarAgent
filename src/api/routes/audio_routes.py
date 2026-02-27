"""音频处理路由"""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.api.schemas.models import SynthesizeRequest, VoiceItem, StatusResponse
from src.audio.tts import TTSEngine
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

tts_engine = TTSEngine()


@router.get("/voices", response_model=list[VoiceItem])
async def list_voices():
    """获取可用音色列表"""
    return tts_engine.list_voices()


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    """语音合成"""
    audio_path = await tts_engine.synthesize(req.text, req.voice_id, req.speed)
    return FileResponse(audio_path, media_type="audio/wav", filename="synthesized.wav")


@router.get("/service/status")
async def tts_service_status():
    """检查 CosyVoice 服务状态"""
    online = await tts_engine.check_service()
    return {"status": "online" if online else "offline"}
