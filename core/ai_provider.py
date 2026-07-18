"""
AI Provider 抽象层 — 混合 AI 架构
支持本地（默认）+ 可选云端（OpenAI / Anthropic）
"""

import os
import warnings
from abc import ABC, abstractmethod
from typing import List


class AIProvider(ABC):
    """AI 提供者抽象基类"""

    @abstractmethod
    def summarize(self, text: str, max_length: int = 200) -> str:
        """生成文本摘要"""

    @abstractmethod
    def answer(self, question: str, context: str) -> str:
        """基于上下文回答问题"""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """生成文本向量。不支持时返回 []"""


def create_provider() -> AIProvider:
    """
    根据环境变量创建 AI Provider。

    优先级：
    1. MEMOMIND_AI_PROVIDER=openai → OpenAIProvider（需要 OPENAI_API_KEY）
    2. MEMOMIND_AI_PROVIDER=anthropic → AnthropicProvider（需要 ANTHROPIC_API_KEY）
    3. 默认 → LocalProvider

    如果指定的 provider 缺少 API key，会 warning 并 fallback 到 LocalProvider。
    """
    from .ai_local import LocalProvider

    provider_name = os.environ.get("MEMOMIND_AI_PROVIDER", "local").lower()

    if provider_name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            warnings.warn(
                "OPENAI_API_KEY 未设置，AI Provider 回退到本地模式。"
                "如需使用 OpenAI，请设置 OPENAI_API_KEY 环境变量。",
                UserWarning,
            )
            return LocalProvider()

        from .ai_openai import OpenAIProvider
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        embed_model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        base_url = os.environ.get("OPENAI_BASE_URL", "")
        embed_base_url = os.environ.get("OPENAI_EMBED_BASE_URL", "")
        return OpenAIProvider(
            api_key=api_key, model=model, embed_model=embed_model,
            base_url=base_url, embed_base_url=embed_base_url,
        )

    elif provider_name == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            warnings.warn(
                "ANTHROPIC_API_KEY 未设置，AI Provider 回退到本地模式。"
                "如需使用 Anthropic，请设置 ANTHROPIC_API_KEY 环境变量。",
                UserWarning,
            )
            return LocalProvider()

        from .ai_anthropic import AnthropicProvider
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        return AnthropicProvider(api_key=api_key, model=model, base_url=base_url)

    # 默认：本地模式
    return LocalProvider()
