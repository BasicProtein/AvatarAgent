"""视频号发布器

通过 Playwright 自动化操作微信视频号发布视频。
"""

import asyncio
from pathlib import Path

from src.uploader.base import BaseUploader
from src.common.logger import get_logger
from src.common.exceptions import UploadError

logger = get_logger(__name__)


class ShipinhaoUploader(BaseUploader):
    """视频号平台发布器"""

    @property
    def platform_name(self) -> str:
        return "视频号"

    async def _do_publish(
        self,
        video_path: str,
        description: str,
        cover_path: str,
        tags: list[str],
    ) -> bool:
        """视频号发布逻辑"""
        playwright = None
        browser = None

        try:
            playwright, browser, context = await self._get_browser_context()
            page = await context.new_page()

            # 打开视频号创作者中心
            await page.goto("https://channels.weixin.qq.com/platform/post/create")
            await page.wait_for_load_state("networkidle", timeout=30000)

            # 等待上传区域加载
            upload_input = page.locator('input[type="file"]')
            await upload_input.wait_for(timeout=15000)

            # 上传视频文件
            await upload_input.set_input_files(video_path)
            logger.info("已选择视频文件，等待上传完成...")

            # 等待上传完成
            await page.wait_for_selector(
                'button:has-text("发表"), .weui-desktop-btn_primary',
                timeout=120000,
            )
            logger.info("视频上传完成")

            # 填写描述
            desc_editor = page.locator(
                '.input-editor, '
                'div[contenteditable="true"], '
                'textarea'
            ).first
            await desc_editor.wait_for(timeout=10000)
            await desc_editor.click()

            # 组合描述和标签
            full_text = description
            if tags:
                tag_str = " ".join(f"#{t}" for t in tags)
                full_text = f"{description} {tag_str}"

            await desc_editor.fill("")
            await desc_editor.type(full_text, delay=30)
            logger.info(f"已填写视频描述: {full_text[:50]}...")

            # 设置封面
            if cover_path and Path(cover_path).exists():
                try:
                    cover_btn = page.locator(
                        'text="设置封面", text="更换封面"'
                    ).first
                    if await cover_btn.is_visible():
                        await cover_btn.click()
                        await asyncio.sleep(1)

                        cover_input = page.locator(
                            'input[accept*="image"]'
                        ).first
                        if await cover_input.is_visible():
                            await cover_input.set_input_files(cover_path)
                            await asyncio.sleep(2)

                            confirm_btn = page.locator(
                                'button:has-text("完成"), button:has-text("确定")'
                            ).first
                            if await confirm_btn.is_visible():
                                await confirm_btn.click()
                                logger.info("已设置视频封面")
                except Exception as e:
                    logger.warning(f"设置封面失败（非致命错误）: {e}")

            await asyncio.sleep(2)

            # 点击发表按钮
            publish_btn = page.locator(
                'button:has-text("发表"), .weui-desktop-btn_primary'
            ).first
            await publish_btn.click()
            logger.info("已点击发表按钮")

            # 等待发布结果
            await asyncio.sleep(5)

            # 检查发布状态
            success_msg = page.locator('text="发表成功"')
            if await success_msg.is_visible():
                logger.info("视频号发布成功")
                return True

            current_url = page.url
            if "create" not in current_url:
                logger.info("视频号发布成功（页面已跳转）")
                return True

            logger.warning("视频号发布状态不确定，请手动确认")
            return True

        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright:
                await playwright.stop()
