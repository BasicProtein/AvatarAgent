"""文案处理路由"""

from fastapi import APIRouter

from src.api.schemas.models import (
    ExtractRequest,
    ExtractResponse,
    RewriteRequest,
    DescriptionRequest,
    StatusResponse,
)
from src.script.extractor import ScriptExtractor
from src.script.rewriter import ScriptRewriter
from src.common.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
async def extract_script(req: ExtractRequest):
    """提取视频文案"""
    extractor = ScriptExtractor()
    try:
        text = extractor.extract_from_url(req.video_url)
        return ExtractResponse(text=text)
    finally:
        extractor.cleanup()


@router.post("/rewrite", response_model=ExtractResponse)
async def rewrite_script(req: RewriteRequest):
    """文案仿写"""
    rewriter = ScriptRewriter()
    if req.mode == "custom" and req.prompt:
        text = await rewriter.rewrite_with_prompt(req.text, req.prompt, req.api_key)
    else:
        text = await rewriter.rewrite_auto(req.text, req.api_key)
    return ExtractResponse(text=text)


@router.post("/description", response_model=ExtractResponse)
async def generate_description(req: DescriptionRequest):
    """生成视频描述和话题标签"""
    rewriter = ScriptRewriter()
    text = await rewriter.generate_description(req.text, req.api_key)
    return ExtractResponse(text=text)
