"""FastAPI 主应用

启动入口和路由注册。
"""

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 将项目根目录加入 PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""

    app = FastAPI(
        title="AvatarAgent API",
        description="AI 数字人口播视频自动化生成工具 API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    from src.api.routes.script_routes import router as script_router
    from src.api.routes.audio_routes import router as audio_router
    from src.api.routes.avatar_routes import router as avatar_router
    from src.api.routes.video_routes import router as video_router
    from src.api.routes.upload_routes import router as upload_router
    from src.api.routes.pipeline_routes import router as pipeline_router
    from src.api.routes.config_routes import router as config_router

    app.include_router(script_router, prefix="/api/script", tags=["文案处理"])
    app.include_router(audio_router, prefix="/api/audio", tags=["音频处理"])
    app.include_router(avatar_router, prefix="/api/avatar", tags=["数字人"])
    app.include_router(video_router, prefix="/api/video", tags=["视频后期"])
    app.include_router(upload_router, prefix="/api/upload", tags=["平台发布"])
    app.include_router(pipeline_router, prefix="/api/pipeline", tags=["全流程"])
    app.include_router(config_router, prefix="/api/config", tags=["配置管理"])

    # 挂载输出目录为静态文件
    output_dir = ConfigManager().get_output_dir()
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "AvatarAgent"}

    logger.info("FastAPI 应用已创建")
    return app


# 应用实例
app = create_app()
