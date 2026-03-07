"""AvatarAgent 统一启动器

启动 FastAPI 后端服务。
"""

import os
import sys
from pathlib import Path

# 确保项目根目录在 PYTHONPATH 中
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager

logger = get_logger(__name__)


def main():
    """启动 AvatarAgent 后端服务"""
    import uvicorn

    config = ConfigManager()

    host = config.get("server", "host", "0.0.0.0")
    port = config.get_int("server", "port", 8000)

    # 设置 FFmpeg 环境变量
    ffmpeg_path = config.get("ffmpeg", "bin_path", "")
    if ffmpeg_path:
        # bin_path 可能是文件路径（如 ffmpeg.exe）或目录路径，统一取其所在目录
        ffmpeg_dir = os.path.dirname(ffmpeg_path) if os.path.isfile(ffmpeg_path) else ffmpeg_path
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ["FFMPEG_PATH"] = ffmpeg_path

    logger.info(f"启动 AvatarAgent 后端服务: http://{host}:{port}")
    logger.info(f"API 文档: http://{host}:{port}/docs")

    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
