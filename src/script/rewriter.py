"""AI 文案仿写模块

基于 Deepseek API 实现文案仿写、视频描述生成、话题标签生成。
支持两种模式：AI 自动仿写 和 自定义指令仿写。
"""

from typing import Optional

import httpx

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import ScriptRewriteError

logger = get_logger(__name__)

# Deepseek API 端点
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 默认系统提示词
AUTO_REWRITE_SYSTEM_PROMPT = """你是一位专业的短视频口播文案改写专家。请对以下文案进行语义级仿写与结构重组：
1. 保留核心观点和论述逻辑
2. 更换表达方式和遣词造句
3. 调整段落结构和行文顺序
4. 确保仿写后的文案自然流畅、适合口播
5. 保持原文案的情感基调和目标受众
6. 只输出仿写后的文案正文，不要输出任何标注或标签"""

DESCRIPTION_SYSTEM_PROMPT = """你是一位短视频运营专家。请根据以下口播文案，生成：
第一行：一句吸引人的视频描述（15-30字）
第二行：3-5个相关话题标签，格式为 #话题1 #话题2 #话题3
只输出这两行内容，不需要其他说明。"""


class ScriptRewriter:
    """基于 Deepseek API 的文案仿写器"""

    def __init__(self) -> None:
        self.config = ConfigManager()

    async def rewrite_auto(self, text: str, api_key: str) -> str:
        """AI 自动仿写

        Args:
            text: 原始文案
            api_key: Deepseek API Key

        Returns:
            仿写后的文案

        Raises:
            ScriptRewriteError: 仿写失败
        """
        return await self._call_deepseek(
            system_prompt=AUTO_REWRITE_SYSTEM_PROMPT,
            user_content=text,
            api_key=api_key,
        )

    async def rewrite_with_prompt(
        self, text: str, prompt: str, api_key: str
    ) -> str:
        """自定义指令仿写

        Args:
            text: 原始文案
            prompt: 用户自定义改写指令
            api_key: Deepseek API Key

        Returns:
            仿写后的文案

        Raises:
            ScriptRewriteError: 仿写失败
        """
        system_prompt = f"你是一位专业的文案改写助手。请按照以下要求改写文案：\n{prompt}"
        return await self._call_deepseek(
            system_prompt=system_prompt,
            user_content=text,
            api_key=api_key,
        )

    async def generate_description(self, text: str, api_key: str) -> str:
        """生成视频描述和话题标签

        Args:
            text: 口播文案
            api_key: Deepseek API Key

        Returns:
            视频描述和话题标签文本

        Raises:
            ScriptRewriteError: 生成失败
        """
        return await self._call_deepseek(
            system_prompt=DESCRIPTION_SYSTEM_PROMPT,
            user_content=text,
            api_key=api_key,
        )

    async def _call_deepseek(
        self,
        system_prompt: str,
        user_content: str,
        api_key: str,
        model: str = DEEPSEEK_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """调用 Deepseek API

        Args:
            system_prompt: 系统提示词
            user_content: 用户内容
            api_key: API Key
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            模型回复文本

        Raises:
            ScriptRewriteError: API 调用失败
        """
        if not api_key:
            raise ScriptRewriteError("未提供 Deepseek API Key")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(f"Deepseek API 调用成功，回复长度: {len(content)}")
                return content.strip()

        except httpx.HTTPStatusError as e:
            raise ScriptRewriteError(
                f"Deepseek API 返回错误 {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise ScriptRewriteError(f"Deepseek API 请求失败: {e}") from e
        except (KeyError, IndexError) as e:
            raise ScriptRewriteError(f"Deepseek API 响应格式异常: {e}") from e
