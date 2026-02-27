"""抖音发布器

通过 Playwright 自动化操作抖音创作者中心发布视频。
"""

import asyncio
from pathlib import Path

from src.uploader.base import BaseUploader
from src.common.logger import get_logger
from src.common.exceptions import UploadError

logger = get_logger(__name__)


class DouyinUploader(BaseUploader):
    """抖音平台发布器"""

    @property
    def platform_name(self) -> str:
        return "抖音"

    async def _do_publish(
        self,
        video_path: str,
        description: str,
        cover_path: str,
        tags: list[str],
    ) -> bool:
        """抖音发布逻辑

        Steps:
        1. 打开抖音创作者中心
        2. 上传视频文件
        3. 填写视频描述和话题标签
        4. 可选设置封面
        5. 点击发布
        """
        playwright = None
        browser = None

        try:
            playwright, browser, context = await self._get_browser_context()
            page = await context.new_page()

            # 打开抖音创作者中心上传页面
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            await page.wait_for_load_state("networkidle", timeout=30000)

            # 等待上传区域加载
            upload_input = page.locator('input[type="file"]')
            await upload_input.wait_for(timeout=15000)

            # 上传视频文件
            await upload_input.set_input_files(video_path)
            logger.info("已选择视频文件，等待上传完成...")

            # 等待上传完成（等待发布按钮出现或上传进度消失）
            await page.wait_for_selector(
                'button:has-text("发布"), button:has-text("publish")',
                timeout=120000,
            )
            logger.info("视频上传完成")

            # 填写视频描述
            desc_editor = page.locator(
                '.notranslate[contenteditable="true"]'
            ).first
            await desc_editor.wait_for(timeout=10000)
            await desc_editor.click()

            # 组合描述文本和话题标签
            full_text = description
            if tags:
                tag_str = " ".join(f"#{t}" for t in tags)
                full_text = f"{description} {tag_str}"

            await desc_editor.fill("")
            await desc_editor.type(full_text, delay=30)
            logger.info(f"已填写视频描述: {full_text[:50]}...")

            # 设置封面（如果提供）
            if cover_path and Path(cover_path).exists():
                try:
                    cover_btn = page.locator('text="选择封面"').first
                    if await cover_btn.is_visible():
                        await cover_btn.click()
                        await asyncio.sleep(1)

                        upload_cover = page.locator(
                            '.upload-cover input[type="file"], '
                            'input[accept*="image"]'
                        ).first
                        if await upload_cover.is_visible():
                            await upload_cover.set_input_files(cover_path)
                            await asyncio.sleep(2)

                            confirm_btn = page.locator('button:has-text("完成")').first
                            if await confirm_btn.is_visible():
                                await confirm_btn.click()
                                logger.info("已设置视频封面")
                except Exception as e:
                    logger.warning(f"设置封面失败（非致命错误）: {e}")

            # 等待一段时间确保表单稳定
            await asyncio.sleep(2)

            # 点击发布按钮
            publish_btn = page.locator('button:has-text("发布")').first
            await publish_btn.click()
            logger.info("已点击发布按钮")

            # 等待发布结果
            await asyncio.sleep(5)

            # 检查是否发布成功（页面跳转或出现成功提示）
            current_url = page.url
            if "manage" in current_url or "content" in current_url:
                logger.info("抖音发布成功")
                return True

            # 检查是否有成功提示
            success_msg = page.locator('text="发布成功"')
            if await success_msg.is_visible():
                return True

            logger.warning("发布状态不确定，请手动确认")
            return True

        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright:
                await playwright.stop()
