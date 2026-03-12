"""字幕生成与添加模块

基于 FFmpeg 实现字幕的生成（从音频/文本）和嵌入视频。
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import SubtitleError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
FONTS_DIR = PROJECT_ROOT / "resources" / "fonts"

# 可用字体列表（系统自带 + 项目字体）
DEFAULT_FONT_FAMILIES = [
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "KaiTi",
    "FangSong",
    "Arial",
]


def get_font_families() -> list[str]:
    """获取可用字体列表

    Returns:
        字体名称列表
    """
    fonts = list(DEFAULT_FONT_FAMILIES)
    if FONTS_DIR.exists():
        for f in FONTS_DIR.iterdir():
            if f.suffix.lower() in (".ttf", ".otf", ".ttc"):
                fonts.append(f.stem)
    return fonts


class SubtitleGenerator:
    """字幕生成与添加器"""

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.ffmpeg = self.config.get_ffmpeg_path()

    async def generate_srt(
        self,
        video_path: str,
        text: str = "",
        api_key: str = "",
    ) -> str:
        """生成 SRT 字幕文件

        如果提供了 text，则基于文本和视频时长生成字幕。
        如果未提供 text，则先从视频提取音频，再使用 ASR 识别。

        Args:
            video_path: 视频文件路径
            text: 口播文案文本（可选）
            api_key: API Key（用于 ASR）

        Returns:
            SRT 字幕文件路径

        Raises:
            SubtitleError: 生成失败
        """
        video_path = self._resolve_video_path(video_path)
        if not Path(video_path).exists():
            raise SubtitleError(f"视频文件不存在: {video_path}")

        try:
            output_dir = self.config.get_output_dir() / "subtitle"
            ensure_dir(output_dir)
            srt_path = str(output_dir / generate_unique_filename("srt", "sub"))

            if text:
                # 基于文本和视频时长生成简单字幕
                duration = self._get_media_duration(video_path)
                srt_content = self._text_to_srt(text, duration)
            else:
                # 先提取音频，再使用 ASR 带时间戳转录
                audio_path = self._extract_audio(video_path, output_dir)
                from src.audio.asr import ASREngine
                asr = ASREngine()
                segments = await asr.transcribe_with_timestamps(audio_path)
                srt_content = self._segments_to_srt(segments)

            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)

            logger.info(f"字幕文件生成完成: {srt_path}")
            return srt_path

        except Exception as e:
            raise SubtitleError(f"字幕生成失败: {e}") from e

    async def add_to_video(
        self,
        video_path: str,
        srt_path: str = "",
        font_family: str = "Microsoft YaHei",
        font_size: int = 11,
        font_color: str = "#FFFFFF",
        outline_color: str = "#000000",
        bottom_margin: int = 60,
    ) -> str:
        """将字幕添加到视频

        Args:
            video_path: 视频文件路径
            srt_path: SRT 字幕文件路径（为空则自动从视频提取音频生成）
            font_family: 字体名称
            font_size: 字体大小
            font_color: 字体颜色（十六进制）
            outline_color: 描边颜色（十六进制）
            bottom_margin: 底部边距

        Returns:
            带字幕的视频文件路径

        Raises:
            SubtitleError: 添加失败
        """
        video_path = self._resolve_video_path(video_path)
        if not Path(video_path).exists():
            raise SubtitleError(f"视频文件不存在: {video_path}")

        if srt_path and not Path(srt_path).exists():
            raise SubtitleError(f"字幕文件不存在: {srt_path}")

        try:
            output_dir = self.config.get_output_dir() / "video"
            ensure_dir(output_dir)
            output_path = str(output_dir / generate_unique_filename("mp4", "subtitled"))

            # 构建 FFmpeg 字幕滤镜
            # 颜色转换: #FFFFFF -> &HFFFFFF&
            fc = self._hex_to_ass_color(font_color)
            oc = self._hex_to_ass_color(outline_color)

            # Windows 路径：统一用正斜杠，并转义冒号（FFmpeg filtergraph 把 : 当参数分隔符）
            srt_path_fwd = srt_path.replace("\\", "/").replace(":", "\\:")

            subtitle_filter = (
                f"subtitles=filename='{srt_path_fwd}':force_style='"
                f"FontName={font_family},"
                f"FontSize={font_size},"
                f"PrimaryColour={fc},"
                f"OutlineColour={oc},"
                f"Outline=2,"
                f"MarginV={bottom_margin}'"
            )

            cmd = [
                self.ffmpeg,
                "-i", video_path,
                "-vf", subtitle_filter,
                "-c:a", "copy",
                "-y",
                output_path,
            ]

            logger.info(f"[subtitle] FFmpeg 命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                logger.error(f"[subtitle] FFmpeg stderr: {result.stderr[-2000:]}")
                raise SubtitleError(f"FFmpeg 字幕添加失败: {result.stderr[-500:]}")

            logger.info(f"字幕已添加到视频: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            raise SubtitleError("字幕添加超时")
        except SubtitleError:
            raise
        except Exception as e:
            raise SubtitleError(f"字幕添加失败: {e}") from e

    def _resolve_video_path(self, video_path: str) -> str:
        """将容器内裸路径（如 /uuid-r.mp4）解析为宿主机 output/avatar/ 路径"""
        p = Path(video_path)
        # 已是宿主机绝对路径且存在，直接返回
        if p.exists():
            return video_path
        # 容器内路径：以 / 开头但在宿主机不存在（如 /uuid-r.mp4 或 /code/data/temp/uuid-r.mp4）
        if video_path.startswith("/"):
            avatar_dir = self.config.get_output_dir() / "avatar"
            candidate = avatar_dir / p.name
            if candidate.exists():
                logger.info(f"[subtitle] 路径映射: {video_path} → {candidate}")
                return str(candidate)
        return video_path

    def _get_ffprobe_path(self) -> str:
        """从 ffmpeg 路径推导出 ffprobe 路径"""
        p = Path(self.ffmpeg)
        ffprobe = p.parent / ("ffprobe" + p.suffix)
        return str(ffprobe) if ffprobe.exists() else "ffprobe"

    def _get_media_duration(self, media_path: str) -> float:
        """获取音视频文件时长（秒）"""
        cmd = [
            self._get_ffprobe_path(),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            media_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(result.stdout.strip())

    def _extract_audio(self, video_path: str, output_dir: Path) -> str:
        """从视频提取音频 WAV 文件，供 ASR 使用"""
        audio_path = str(output_dir / generate_unique_filename("wav", "audio"))
        cmd = [
            self.ffmpeg,
            "-i", video_path,
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise SubtitleError(f"音频提取失败: {result.stderr}")
        return audio_path

    def _text_to_srt(self, text: str, duration: float) -> str:
        """将文本按句分割生成简单 SRT"""
        import re
        # 按标点分句
        sentences = re.split(r'[。！？.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return ""

        time_per_sentence = duration / len(sentences)
        srt_lines = []

        for i, sentence in enumerate(sentences):
            start = i * time_per_sentence
            end = (i + 1) * time_per_sentence
            srt_lines.append(f"{i + 1}")
            srt_lines.append(
                f"{self._seconds_to_srt_time(start)} --> {self._seconds_to_srt_time(end)}"
            )
            srt_lines.append(sentence)
            srt_lines.append("")

        return "\n".join(srt_lines)

    def _segments_to_srt(self, segments: list[dict]) -> str:
        """将 ASR 时间戳段转为 SRT 格式"""
        srt_lines = []
        for i, seg in enumerate(segments):
            srt_lines.append(f"{i + 1}")
            srt_lines.append(
                f"{self._seconds_to_srt_time(seg['start'])} --> "
                f"{self._seconds_to_srt_time(seg['end'])}"
            )
            srt_lines.append(seg["text"])
            srt_lines.append("")
        return "\n".join(srt_lines)

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """秒数转 SRT 时间格式 (HH:MM:SS,mmm)"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    @staticmethod
    def _hex_to_ass_color(hex_color: str) -> str:
        """十六进制颜色转 ASS 字幕颜色格式"""
        hex_color = hex_color.lstrip("#")
        r, g, b = hex_color[:2], hex_color[2:4], hex_color[4:6]
        return f"&H{b}{g}{r}&"
