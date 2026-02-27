"""发布器基类

定义多平台发布的通用接口和 Chrome 调试端口管理。
"""

import os
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import UploadError

logger = get_logger(__name__)


class BaseUploader(ABC):
    """平台发布器基类

    提供 Playwright + Chrome 调试端口的通用基础设施。
    子类只需实现 _do_publish 方法即可。
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.debug_port = self.config.get_int("browser", "debug_port", 9222)
        self.chrome_path = self.config.get("browser", "LOCAL_CHROME_PATH", "")

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        ...

    async def publish(
        self,
        video_path: str,
        description: str,
        cover_path: str = "",
        tags: list[str] | None = None,
    ) -> bool:
        """发布视频到平台

        Args:
            video_path: 视频文件路径
            description: 视频描述
            cover_path: 封面图片路径（可选）
            tags: 话题标签列表（可选）

        Returns:
            是否发布成功

        Raises:
            UploadError: 发布失败
        """
        if not Path(video_path).exists():
            raise UploadError(f"视频文件不存在: {video_path}")

        if cover_path and not Path(cover_path).exists():
            raise UploadError(f"封面文件不存在: {cover_path}")

        logger.info(f"开始发布到 {self.platform_name}: {video_path}")

        try:
            result = await self._do_publish(
                video_path=video_path,
                description=description,
                cover_path=cover_path,
                tags=tags or [],
            )
            if result:
                logger.info(f"发布到 {self.platform_name} 成功")
            else:
                logger.warning(f"发布到 {self.platform_name} 失败")
            return result

        except Exception as e:
            raise UploadError(f"发布到 {self.platform_name} 失败: {e}") from e

    @abstractmethod
    async def _do_publish(
        self,
        video_path: str,
        description: str,
        cover_path: str,
        tags: list[str],
    ) -> bool:
        """实际发布逻辑，由子类实现"""
        ...

    async def _get_browser_context(self):
        """获取 Playwright 浏览器上下文（通过 Chrome 调试端口）

        Returns:
            (playwright, browser, context) 元组
        """
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()

        try:
            browser = await playwright.chromium.connect_over_cdp(
                f"http://localhost:{self.debug_port}"
            )
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            return playwright, browser, context

        except Exception as e:
            await playwright.stop()
            raise UploadError(
                f"无法连接 Chrome 调试端口 {self.debug_port}。"
                f"请确保已启动带调试端口的 Chrome: "
                f'chrome.exe --remote-debugging-port={self.debug_port}'
            ) from e
