"""AI 法务审查模块

基于违禁词库 + Deepseek API 实现文案合规审查。
- 本地违禁词快速扫描
- AI 深度合规审查（识别不合规表达、语境风险）
"""

import json
import re
from pathlib import Path
from typing import Any

import httpx

from src.common.logger import get_logger
from src.common.exceptions import ComplianceCheckError

logger = get_logger(__name__)

# Deepseek API 端点（与 rewriter 共用）
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 违禁词库路径
PROHIBITED_WORDS_PATH = Path(__file__).parent.parent.parent / "resources" / "compliance" / "prohibited_words.txt"

# AI 合规审查提示词
COMPLIANCE_SYSTEM_PROMPT = """你是一位专业的短视频内容法务合规审查专家。请审查以下口播文案，识别可能存在的合规风险：

审查维度：
1. 绝对化用语（如"最好"、"第一"、"唯一"等广告法禁用词）
2. 虚假/夸大宣传（不实承诺、夸大效果）
3. 医疗健康违规声明（未经证实的疗效、偏方推荐）
4. 金融理财违规（保本承诺、收益保证）
5. 引流/导流风险（提及竞品平台、引导私域）
6. 低俗不当表达
7. 其他平台发布可能触发审核的内容

请以 JSON 格式输出审查结果，格式如下：
{
  "issues": [
    {
      "original": "问题原文片段",
      "suggestion": "建议修改为",
      "reason": "违规原因说明"
    }
  ],
  "revised_text": "修正后的完整文案（如果没有问题则原样返回）"
}

注意：
- 如果文案没有任何问题，issues 返回空数组，revised_text 原样返回
- 只输出 JSON，不要输出其他说明文字
- 修正文案时保持原文语气和风格，只替换违规部分"""


class ComplianceChecker:
    """文案合规审查器

    结合本地违禁词库和 AI 深度审查，提供完整的合规检测。
    """

    def __init__(self) -> None:
        self._prohibited_words: dict[str, str] = {}  # word -> category
        self._load_prohibited_words()

    def _load_prohibited_words(self) -> None:
        """加载违禁词库"""
        if not PROHIBITED_WORDS_PATH.exists():
            logger.warning(f"违禁词库不存在: {PROHIBITED_WORDS_PATH}")
            return

        current_category = "未分类"
        for line in PROHIBITED_WORDS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("# ==="):
                # 主分类标题，如 "# ==================== 广告法违禁词 ===================="
                match = re.search(r"=+\s*(.+?)\s*=+", line)
                if match:
                    current_category = match.group(1)
                continue
            if line.startswith("# ---"):
                # 子分类标题，如 "# --- 绝对化用语 ---"
                match = re.search(r"---\s*(.+?)\s*---", line)
                if match:
                    current_category = match.group(1)
                continue
            if line.startswith("#"):
                continue
            self._prohibited_words[line] = current_category

        logger.info(f"已加载 {len(self._prohibited_words)} 个违禁词")

    def check_prohibited_words(self, text: str) -> list[dict[str, Any]]:
        """本地违禁词扫描

        Args:
            text: 待审查文案

        Returns:
            命中的违禁词列表，每项包含 word, position, category
        """
        hits: list[dict[str, Any]] = []
        seen: set[str] = set()

        for word, category in self._prohibited_words.items():
            if word in text and word not in seen:
                seen.add(word)
                position = text.index(word)
                hits.append({
                    "word": word,
                    "position": position,
                    "category": category,
                })

        # 按出现位置排序
        hits.sort(key=lambda x: x["position"])
        logger.info(f"违禁词扫描完成，命中 {len(hits)} 个")
        return hits

    async def check_compliance_ai(self, text: str, api_key: str) -> dict[str, Any]:
        """AI 深度合规审查

        Args:
            text: 待审查文案
            api_key: Deepseek API Key

        Returns:
            包含 issues 和 revised_text 的审查结果

        Raises:
            ComplianceCheckError: API 调用失败
        """
        if not api_key:
            raise ComplianceCheckError("未提供 Deepseek API Key")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,  # 低温度，更精确的审查
            "max_tokens": 2048,
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
                content = data["choices"][0]["message"]["content"].strip()

                # 尝试解析 JSON（AI 可能包裹 markdown 代码块）
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\s*", "", content)
                    content = re.sub(r"\s*```$", "", content)

                result = json.loads(content)
                logger.info(
                    f"AI 合规审查完成，发现 {len(result.get('issues', []))} 个问题"
                )
                return result

        except json.JSONDecodeError as e:
            logger.warning(f"AI 返回格式异常，尝试容错处理: {e}")
            # 容错：如果 JSON 解析失败，返回无问题结果
            return {"issues": [], "revised_text": text}
        except httpx.HTTPStatusError as e:
            raise ComplianceCheckError(
                f"Deepseek API 返回错误 {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise ComplianceCheckError(f"Deepseek API 请求失败: {e}") from e
        except (KeyError, IndexError) as e:
            raise ComplianceCheckError(f"Deepseek API 响应格式异常: {e}") from e

    async def review(self, text: str, api_key: str) -> dict[str, Any]:
        """执行完整合规审查（违禁词 + AI 审查）

        Args:
            text: 待审查文案
            api_key: Deepseek API Key

        Returns:
            完整审查结果：
            {
                "passed": bool,
                "prohibited_words": [...],
                "ai_suggestions": [...],
                "revised_text": str
            }
        """
        # 1. 本地违禁词扫描
        prohibited_hits = self.check_prohibited_words(text)

        # 2. AI 深度审查
        ai_result = await self.check_compliance_ai(text, api_key)
        ai_suggestions = ai_result.get("issues", [])
        revised_text = ai_result.get("revised_text", text)

        # 3. 综合判定
        passed = len(prohibited_hits) == 0 and len(ai_suggestions) == 0

        return {
            "passed": passed,
            "prohibited_words": prohibited_hits,
            "ai_suggestions": ai_suggestions,
            "revised_text": revised_text,
        }
