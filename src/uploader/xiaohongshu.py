"""小红书发布器

通过 Playwright 自动化操作小红书创作者中心发布视频。
"""

import asyncio
from pathlib import Path

from src.uploader.base import BaseUploader
from src.common.logger import get_logger
from src.common.exceptions import UploadError

logger = get_logger(__name__)


class XiaohongshuUploader(BaseUploader):
    """小红书平台发布器"""

    @property
    def platform_name(self) -> str:
        return "小红书"

    async def _do_publish(
        self,
        video_path: str,
        description: str,
        cover_path: str,
        tags: list[str],
    ) -> bool:
        """小红书发布逻辑"""
        playwright = None
        browser = None

        try:
            playwright, browser, context = await self._get_browser_context()
            page = await context.new_page()

            # 打开小红书创作者中心
            await page.goto("https://creator.xiaohongshu.com/publish/publish")
            await page.wait_for_load_state("networkidle", timeout=30000)

            # 等待上传区域加载
            upload_input = page.locator('input[type="file"]')
            await upload_input.wait_for(timeout=15000)

            # 上传视频文件
            await upload_input.set_input_files(video_path)
            logger.info("已选择视频文件，等待上传完成...")

            # 等待上传+处理完成
            await page.wait_for_selector(
                'button:has-text("发布"), .publish-btn',
                timeout=120000,
            )
            logger.info("视频上传完成")

            # 填写标题（小红书有标题字段）
            title_input = page.locator(
                'input[placeholder*="标题"], input[placeholder*="填写标题"]'
            ).first
            if await title_input.is_visible():
                # 用描述的前20个字作为标题
                title_text = description[:20] if len(description) > 20 else description
                await title_input.fill(title_text)
                logger.info(f"已填写标题: {title_text}")

            # 填写正文描述
            desc_editor = page.locator(
                '.ql-editor[contenteditable="true"], '
                '#post-textarea, '
                '.notranslate[contenteditable="true"]'
            ).first
            await desc_editor.wait_for(timeout=10000)
            await desc_editor.click()

            # 组合描述和话题
            full_text = description
            if tags:
                tag_str = " ".join(f"#{t}" for t in tags)
                full_text = f"{description} {tag_str}"

            await desc_editor.fill("")
            await desc_editor.type(full_text, delay=30)
            logger.info(f"已填写描述: {full_text[:50]}...")

            # 设置封面
            if cover_path and Path(cover_path).exists():
                try:
                    cover_input = page.locator(
                        '.cover-upload input[type="file"], '
                        'input[accept*="image"]'
                    ).first
                    if await cover_input.is_visible():
                        await cover_input.set_input_files(cover_path)
                        await asyncio.sleep(2)
                        logger.info("已设置封面")
                except Exception as e:
                    logger.warning(f"设置封面失败（非致命错误）: {e}")

            await asyncio.sleep(2)

            # 点击发布按钮
            publish_btn = page.locator(
                'button:has-text("发布"), .publishBtn, .publish-btn'
            ).first
            await publish_btn.click()
            logger.info("已点击发布按钮")

            # 等待发布结果
            await asyncio.sleep(5)

            # 检查发布状态
            success_msg = page.locator('text="发布成功"')
            if await success_msg.is_visible():
                logger.info("小红书发布成功")
                return True

            current_url = page.url
            if "publish" not in current_url:
                logger.info("小红书发布成功（页面已跳转）")
                return True

            logger.warning("小红书发布状态不确定，请手动确认")
            return True

        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright:
                await playwright.stop()
