"""视频封面生成模块

从视频抽帧，叠加文案文字生成封面图片。
支持 AI 自动生成封面文案和手动指定文案两种模式。
"""

import subprocess
from pathlib import Path
from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import CoverError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent


class CoverGenerator:
    """视频封面生成器"""

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.ffmpeg = self.config.get_ffmpeg_path()

    async def generate(
        self,
        video_path: str,
        text: str,
        highlight_words: str = "",
        font_family: str = "SimHei",
        font_size: int = 60,
        font_color: str = "#FFFFFF",
        highlight_color: str = "#FFD600",
        position: str = "bottom",
        frame_time: Optional[float] = None,
        max_width: float = 0.8,
        outline_size: int = 4,
        outline_color: str = "#000000",
    ) -> str:
        """生成视频封面

        Args:
            video_path: 视频文件路径
            text: 封面文案
            highlight_words: 高亮关键词（逗号分隔）
            font_family: 字体名称
            font_size: 字体大小
            font_color: 字体颜色
            highlight_color: 高亮颜色
            position: 文字位置 (top/center/bottom)
            frame_time: 抽帧时间点（秒），None 则使用第1秒
            max_width: 文字最大宽度比例
            outline_size: 描边大小
            outline_color: 描边颜色

        Returns:
            封面图片路径

        Raises:
            CoverError: 生成失败
        """
        if not Path(video_path).exists():
            raise CoverError(f"视频文件不存在: {video_path}")

        try:
            output_dir = self.config.get_output_dir() / "cover"
            ensure_dir(output_dir)

            # Step 1: 从视频抽帧
            frame_path = str(output_dir / generate_unique_filename("png", "frame"))
            time_point = frame_time if frame_time is not None else 1.0
            self._extract_frame(video_path, frame_path, time_point)

            # Step 2: 在帧上叠加文字
            cover_path = str(output_dir / generate_unique_filename("png", "cover"))
            self._add_text_to_image(
                frame_path,
                cover_path,
                text,
                highlight_words=highlight_words,
                font_family=font_family,
                font_size=font_size,
                font_color=font_color,
                highlight_color=highlight_color,
                position=position,
                outline_size=outline_size,
                outline_color=outline_color,
            )

            logger.info(f"封面生成完成: {cover_path}")
            return cover_path

        except CoverError:
            raise
        except Exception as e:
            raise CoverError(f"封面生成失败: {e}") from e

    async def generate_with_ai(
        self,
        video_path: str,
        api_key: str,
        script_text: str = "",
        **kwargs,
    ) -> str:
        """使用 AI 自动生成封面文案并创建封面

        Args:
            video_path: 视频文件路径
            api_key: Deepseek API Key
            script_text: 视频口播文案（若为空则提示需要提供）
            **kwargs: 其他样式参数（传递给 generate 方法）

        Returns:
            封面图片路径
        """
        import httpx

        if not script_text:
            raise CoverError("请提供视频口播文案用于生成封面标题")

        # 使用 Deepseek API 生成简短封面文案
        cover_prompt = (
            "你是短视频封面文案专家。根据以下口播文案，生成一句简短有力的封面标题。\n"
            "要求：\n"
            "1. 不超过15个字\n"
            "2. 具有吸引力和冲击力\n"
            "3. 突出核心卖点或情感\n"
            "4. 只输出标题文字，不要任何标注\n"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": cover_prompt},
                            {"role": "user", "content": script_text[:500]},
                        ],
                        "max_tokens": 50,
                        "temperature": 0.8,
                    },
                )
                response.raise_for_status()
                data = response.json()
                cover_text = data["choices"][0]["message"]["content"].strip()
                logger.info(f"AI 生成封面文案: {cover_text}")

        except Exception as e:
            raise CoverError(f"AI 封面文案生成失败: {e}") from e

        # 用生成的文案创建封面
        return await self.generate(video_path=video_path, text=cover_text, **kwargs)

    def _extract_frame(self, video_path: str, output_path: str, time_point: float) -> None:
        """从视频中提取指定时间点的帧"""
        cmd = [
            self.ffmpeg,
            "-ss", str(time_point),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise CoverError(f"视频抽帧失败: {result.stderr}")

    def _add_text_to_image(
        self,
        image_path: str,
        output_path: str,
        text: str,
        highlight_words: str = "",
        font_family: str = "SimHei",
        font_size: int = 60,
        font_color: str = "#FFFFFF",
        highlight_color: str = "#FFD600",
        position: str = "bottom",
        outline_size: int = 4,
        outline_color: str = "#000000",
    ) -> None:
        """使用 Pillow 在图片上绘制文字"""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)

            # 尝试加载字体
            try:
                font = ImageFont.truetype(font_family, font_size)
            except OSError:
                # 尝试从项目字体目录加载
                font_path = PROJECT_ROOT / "resources" / "fonts" / f"{font_family}.ttf"
                if font_path.exists():
                    font = ImageFont.truetype(str(font_path), font_size)
                else:
                    font = ImageFont.load_default()
                    logger.warning(f"字体 {font_family} 未找到，使用默认字体")

            # 计算文字位置
            img_w, img_h = img.size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            x = (img_w - text_w) // 2
            if position == "top":
                y = img_h // 10
            elif position == "center":
                y = (img_h - text_h) // 2
            else:  # bottom
                y = img_h - text_h - img_h // 10

            # 绘制描边
            for dx in range(-outline_size, outline_size + 1):
                for dy in range(-outline_size, outline_size + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

            # 绘制文字
            draw.text((x, y), text, font=font, fill=font_color)

            img.save(output_path, quality=95)

        except ImportError:
            raise CoverError("Pillow 未安装，请执行: pip install Pillow")
