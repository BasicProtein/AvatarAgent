"""FFmpeg 视频合成流水线

提供视频格式转换、拼接、合成等工具函数。
"""

import subprocess
from pathlib import Path

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import VideoProcessError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)


class VideoComposer:
    """视频合成器 - 基于 FFmpeg"""

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.ffmpeg = self.config.get_ffmpeg_path()

    async def extract_audio(self, video_path: str, output_format: str = "wav") -> str:
        """从视频中提取音频

        Args:
            video_path: 视频文件路径
            output_format: 输出音频格式

        Returns:
            音频文件路径
        """
        if not Path(video_path).exists():
            raise VideoProcessError(f"视频文件不存在: {video_path}")

        output_dir = self.config.get_output_dir() / "audio"
        ensure_dir(output_dir)
        output_path = str(output_dir / generate_unique_filename(output_format, "extracted"))

        cmd = [
            self.ffmpeg,
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le" if output_format == "wav" else "libmp3lame",
            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise VideoProcessError(f"音频提取失败: {result.stderr}")

        logger.info(f"音频已提取: {output_path}")
        return output_path

    async def get_video_info(self, video_path: str) -> dict:
        """获取视频元信息

        Args:
            video_path: 视频文件路径

        Returns:
            视频信息字典: {"duration", "width", "height", "fps"}
        """
        ffprobe = self.ffmpeg.replace("ffmpeg", "ffprobe") if "ffmpeg" in self.ffmpeg else "ffprobe"

        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise VideoProcessError(f"获取视频信息失败: {result.stderr}")

        import json
        data = json.loads(result.stdout)

        info = {"duration": float(data.get("format", {}).get("duration", 0))}

        # 从视频流获取分辨率和帧率
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                info["width"] = stream.get("width", 0)
                info["height"] = stream.get("height", 0)
                fps_str = stream.get("r_frame_rate", "30/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    info["fps"] = round(int(num) / int(den), 2)
                else:
                    info["fps"] = float(fps_str)
                break

        return info

    async def concat_videos(self, video_paths: list[str]) -> str:
        """拼接多个视频

        Args:
            video_paths: 视频文件路径列表

        Returns:
            拼接后的视频路径
        """
        if not video_paths:
            raise VideoProcessError("视频列表为空")

        for p in video_paths:
            if not Path(p).exists():
                raise VideoProcessError(f"视频文件不存在: {p}")

        output_dir = self.config.get_output_dir() / "video"
        ensure_dir(output_dir)

        # 创建 concat 列表文件
        list_path = str(output_dir / "concat_list.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for p in video_paths:
                f.write(f"file '{p}'\n")

        output_path = str(output_dir / generate_unique_filename("mp4", "concat"))

        cmd = [
            self.ffmpeg,
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise VideoProcessError(f"视频拼接失败: {result.stderr}")

        # 清理临时文件
        Path(list_path).unlink(missing_ok=True)

        logger.info(f"视频拼接完成: {output_path}")
        return output_path

    async def convert_format(
        self,
        video_path: str,
        output_format: str = "mp4",
        codec: str = "libx264",
    ) -> str:
        """视频格式转换

        Args:
            video_path: 输入视频路径
            output_format: 输出格式
            codec: 视频编码器

        Returns:
            转换后的视频路径
        """
        if not Path(video_path).exists():
            raise VideoProcessError(f"视频文件不存在: {video_path}")

        output_dir = self.config.get_output_dir() / "video"
        ensure_dir(output_dir)
        output_path = str(output_dir / generate_unique_filename(output_format, "converted"))

        cmd = [
            self.ffmpeg,
            "-i", video_path,
            "-c:v", codec,
            "-c:a", "aac",
            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise VideoProcessError(f"格式转换失败: {result.stderr}")

        logger.info(f"视频格式转换完成: {output_path}")
        return output_path
