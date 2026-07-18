"""
Anthropic AI Provider
依赖：anthropic SDK
"""

from typing import List
from anthropic import Anthropic
from .ai_provider import AIProvider

_SUMMARIZE_PROMPT = "请用中文简明扼要地总结以下文本，控制在{max_length}字以内：\n\n{text}"
_ANSWER_PROMPT = "请根据以下上下文用中文回答问题。如果上下文中没有相关信息，请回答'根据现有资料无法回答'。\n\n问题：{question}\n\n上下文：{context}"


class AnthropicProvider(AIProvider):
    """Anthropic 协议 AI 提供者（兼容任意 Anthropic 兼容 API）"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6",
                 base_url: str = ""):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = Anthropic(**kwargs)
        self.model = model

    def summarize(self, text: str, max_length: int = 200) -> str:
        prompt = _SUMMARIZE_PROMPT.format(max_length=max_length, text=text)
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max(100, max_length),
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    def answer(self, question: str, context: str) -> str:
        prompt = _ANSWER_PROMPT.format(question=question, context=context)
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    def embed(self, text: str) -> List[float]:
        """Anthropic 尚无 embedding API"""
        return []
