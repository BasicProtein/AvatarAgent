"""视频后期处理路由"""

from fastapi import APIRouter

from src.api.schemas.models import SubtitleRequest, BGMRequest, CoverRequest, StatusResponse
from src.video.subtitle import SubtitleGenerator, get_font_families
from src.video.bgm import BGMManager
from src.video.cover import CoverGenerator
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/fonts")
async def list_fonts():
    """获取可用字体列表"""
    return {"fonts": get_font_families()}


@router.post("/subtitle")
async def add_subtitle(req: SubtitleRequest):
    """生成字幕并添加到视频"""
    gen = SubtitleGenerator()
    srt_path = await gen.generate_srt(req.video_path, req.text, req.api_key)
    video_path = await gen.add_to_video(
        req.video_path,
        srt_path,
        font_family=req.style.font_family,
        font_size=req.style.font_size,
        font_color=req.style.font_color,
        outline_color=req.style.outline_color,
        bottom_margin=req.style.bottom_margin,
    )
    return {"video_path": video_path, "srt_path": srt_path}


@router.get("/bgm")
async def list_bgm():
    """获取 BGM 列表"""
    mgr = BGMManager()
    return {"bgm_list": mgr.list_bgm()}


@router.post("/bgm/add")
async def add_bgm(req: BGMRequest):
    """添加 BGM 到视频"""
    mgr = BGMManager()
    if req.bgm_name:
        # 查找指定 BGM
        bgm_list = mgr.list_bgm()
        bgm_path = next(
            (b["path"] for b in bgm_list if b["name"] == req.bgm_name), None
        )
        if not bgm_path:
            return {"status": "error", "message": f"BGM '{req.bgm_name}' 不存在"}
        video_path = await mgr.add_bgm(req.video_path, bgm_path, req.volume)
    else:
        video_path = await mgr.add_random_bgm(req.video_path, req.volume)
    return {"video_path": video_path}


@router.post("/cover")
async def generate_cover(req: CoverRequest):
    """生成视频封面"""
    gen = CoverGenerator()
    if req.use_ai:
        cover_path = await gen.generate_with_ai(req.video_path, req.api_key)
    else:
        cover_path = await gen.generate(
            video_path=req.video_path,
            text=req.text,
            highlight_words=req.highlight_words,
            font_family=req.font_family,
            font_size=req.font_size,
            font_color=req.font_color,
            highlight_color=req.highlight_color,
            position=req.position,
            frame_time=req.frame_time,
        )
    return {"cover_path": cover_path}
