"""文案处理路由"""

from fastapi import APIRouter

from src.api.schemas.models import (
    ExtractRequest,
    ExtractResponse,
    RewriteRequest,
    DescriptionRequest,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    StatusResponse,
)
from src.script.extractor import ScriptExtractor
from src.script.rewriter import ScriptRewriter
from src.script.compliance import ComplianceChecker
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
    try:
        if req.mode == "custom" and req.prompt:
            text = await rewriter.rewrite_with_prompt(req.text, req.prompt, req.api_key)
        else:
            text = await rewriter.rewrite_auto(req.text, req.api_key)
        return ExtractResponse(text=text)
    except Exception as e:
        logger.error(f"文案仿写失败: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.post("/compliance-check", response_model=ComplianceCheckResponse)
async def compliance_check(req: ComplianceCheckRequest):
    """AI 法务合规审查"""
    checker = ComplianceChecker()
    try:
        result = await checker.review(req.text, req.api_key)
        return ComplianceCheckResponse(**result)
    except Exception as e:
        logger.error(f"合规审查失败: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.post("/description", response_model=ExtractResponse)
async def generate_description(req: DescriptionRequest):
    """生成视频描述和话题标签"""
    rewriter = ScriptRewriter()
    try:
        text = await rewriter.generate_description(req.text, req.api_key)
        return ExtractResponse(text=text)
    except Exception as e:
        logger.error(f"描述生成失败: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})
