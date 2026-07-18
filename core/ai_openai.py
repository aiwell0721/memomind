"""
OpenAI AI Provider
依赖：openai SDK
"""

from typing import List
from openai import OpenAI
from .ai_provider import AIProvider

_SUMMARIZE_PROMPT = "请用中文简明扼要地总结以下文本，控制在{max_length}字以内：\n\n{text}"
_ANSWER_PROMPT = "请根据以下上下文用中文回答问题。如果上下文中没有相关信息，请回答'根据现有资料无法回答'。\n\n问题：{question}\n\n上下文：{context}"


class OpenAIProvider(AIProvider):
    """OpenAI 协议 AI 提供者（兼容 DeepSeek / Groq / Azure 等）"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini",
                 embed_model: str = "text-embedding-3-small",
                 base_url: str = "", embed_base_url: str = ""):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model
        self.embed_model = embed_model
        self.embed_base_url = embed_base_url or base_url

    def summarize(self, text: str, max_length: int = 200) -> str:
        prompt = _SUMMARIZE_PROMPT.format(max_length=max_length, text=text)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max(100, max_length),
        )
        return resp.choices[0].message.content.strip()

    def answer(self, question: str, context: str) -> str:
        prompt = _ANSWER_PROMPT.format(question=question, context=context)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
        )
        return resp.choices[0].message.content.strip()

    def embed(self, text: str) -> List[float]:
        # 如果 embedding 有独立 endpoint，创建独立客户端
        if self.embed_base_url and self.embed_base_url != getattr(self.client, '_base_url', ''):
            embed_client = OpenAI(api_key=self.client.api_key, base_url=self.embed_base_url)
        else:
            embed_client = self.client
        resp = embed_client.embeddings.create(
            model=self.embed_model,
            input=text,
        )
        return resp.data[0].embedding
