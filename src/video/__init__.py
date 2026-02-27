"""视频后期处理模块"""

from src.video.subtitle import SubtitleGenerator
from src.video.bgm import BGMManager
from src.video.cover import CoverGenerator
from src.video.composer import VideoComposer

__all__ = ["SubtitleGenerator", "BGMManager", "CoverGenerator", "VideoComposer"]
