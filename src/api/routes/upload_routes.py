"""平台发布路由"""

from fastapi import APIRouter

from src.api.schemas.models import PublishRequest, StatusResponse
from src.uploader.douyin import DouyinUploader
from src.uploader.xiaohongshu import XiaohongshuUploader
from src.uploader.shipinhao import ShipinhaoUploader
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/douyin")
async def publish_douyin(req: PublishRequest):
    """发布到抖音"""
    uploader = DouyinUploader()
    success = await uploader.publish(
        req.video_path, req.description, req.cover_path, req.tags
    )
    return {"status": "success" if success else "failed", "platform": "douyin"}


@router.post("/xiaohongshu")
async def publish_xiaohongshu(req: PublishRequest):
    """发布到小红书"""
    uploader = XiaohongshuUploader()
    success = await uploader.publish(
        req.video_path, req.description, req.cover_path, req.tags
    )
    return {"status": "success" if success else "failed", "platform": "xiaohongshu"}


@router.post("/shipinhao")
async def publish_shipinhao(req: PublishRequest):
    """发布到视频号"""
    uploader = ShipinhaoUploader()
    success = await uploader.publish(
        req.video_path, req.description, req.cover_path, req.tags
    )
    return {"status": "success" if success else "failed", "platform": "shipinhao"}


@router.post("/all")
async def publish_all(req: PublishRequest):
    """一键发布到所有平台"""
    results = {}
    uploaders = {
        "douyin": DouyinUploader(),
        "xiaohongshu": XiaohongshuUploader(),
        "shipinhao": ShipinhaoUploader(),
    }
    for name, uploader in uploaders.items():
        try:
            success = await uploader.publish(
                req.video_path, req.description, req.cover_path, req.tags
            )
            results[name] = "success" if success else "failed"
        except Exception as e:
            results[name] = f"error: {e}"
            logger.error(f"发布到 {name} 失败: {e}")
    return {"results": results}
