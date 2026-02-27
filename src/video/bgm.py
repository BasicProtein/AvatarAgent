"""背景音乐管理模块

管理 BGM 素材库，支持手动选择或随机选择 BGM 并混合到视频中。
"""

import random
import subprocess
from pathlib import Path
from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import BGMError
from src.common.file_utils import ensure_dir, generate_unique_filename, list_files_by_extension

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
BGM_DIR = PROJECT_ROOT / "resources" / "bgm"


class BGMManager:
    """背景音乐管理器"""

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.ffmpeg = self.config.get_ffmpeg_path()
        ensure_dir(BGM_DIR)

    def list_bgm(self) -> list[dict]:
        """获取可用背景音乐列表

        Returns:
            BGM 列表，每项 {"name": str, "path": str}
        """
        files = list_files_by_extension(BGM_DIR, [".mp3", ".wav", ".flac", ".aac", ".m4a"])
        return [{"name": f.stem, "path": str(f)} for f in files]

    async def add_bgm(
        self,
        video_path: str,
        bgm_path: str,
        volume: float = 0.5,
    ) -> str:
        """添加背景音乐到视频

        Args:
            video_path: 视频文件路径
            bgm_path: BGM 文件路径
            volume: BGM 音量 (0.0-1.0)

        Returns:
            带 BGM 的视频文件路径

        Raises:
            BGMError: 处理失败
        """
        if not Path(video_path).exists():
            raise BGMError(f"视频文件不存在: {video_path}")
        if not Path(bgm_path).exists():
            raise BGMError(f"BGM 文件不存在: {bgm_path}")

        try:
            output_dir = self.config.get_output_dir() / "video"
            ensure_dir(output_dir)
            output_path = str(output_dir / generate_unique_filename("mp4", "bgm"))

            # FFmpeg 混音：视频原声 + BGM（循环、降低音量）
            cmd = [
                self.ffmpeg,
                "-i", video_path,
                "-stream_loop", "-1",  # BGM 循环播放
                "-i", bgm_path,
                "-filter_complex",
                f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]",
                "-map", "0:v",
                "-map", "[out]",
                "-c:v", "copy",
                "-shortest",
                "-y",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise BGMError(f"FFmpeg BGM 混音失败: {result.stderr}")

            logger.info(f"BGM 已添加到视频: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            raise BGMError("BGM 添加超时")
        except BGMError:
            raise
        except Exception as e:
            raise BGMError(f"BGM 添加失败: {e}") from e

    async def add_random_bgm(
        self,
        video_path: str,
        volume: float = 0.5,
    ) -> str:
        """随机选择 BGM 并添加到视频

        Args:
            video_path: 视频文件路径
            volume: BGM 音量

        Returns:
            带 BGM 的视频文件路径

        Raises:
            BGMError: 处理失败
        """
        bgm_list = self.list_bgm()
        if not bgm_list:
            raise BGMError("没有可用的 BGM，请在 resources/bgm/ 目录放置音乐文件")

        chosen = random.choice(bgm_list)
        logger.info(f"随机选择 BGM: {chosen['name']}")

        return await self.add_bgm(video_path, chosen["path"], volume)

    async def add_user_bgm(
        self,
        video_path: str,
        user_bgm_path: str,
        volume: float = 0.5,
    ) -> str:
        """使用用户上传的 BGM 添加到视频

        Args:
            video_path: 视频文件路径
            user_bgm_path: 用户上传的 BGM 路径
            volume: BGM 音量

        Returns:
            带 BGM 的视频文件路径
        """
        return await self.add_bgm(video_path, user_bgm_path, volume)
