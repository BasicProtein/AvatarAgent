"""全流程路由"""

from fastapi import APIRouter

from src.api.schemas.models import PipelineRequest
from src.pipeline.orchestrator import PipelineOrchestrator
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/run")
async def run_pipeline(req: PipelineRequest):
    """一键执行全流程"""
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.run_full_pipeline(
        video_url=req.video_url,
        api_key=req.api_key,
        voice_id=req.voice_id,
        model_name=req.model_name,
        speed=req.speed,
        skip_bgm=req.skip_bgm,
        create_cover=req.create_cover,
        publish_platforms=req.publish_platforms,
        description=req.description,
        avatar_engine=req.avatar_engine,
        subtitle_style=req.subtitle_style.model_dump(),
        bgm_volume=req.bgm_volume,
    )
    return result
