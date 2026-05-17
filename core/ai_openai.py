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
    """OpenAI AI 提供者"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", embed_model: str = "text-embedding-3-small"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.embed_model = embed_model

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
        resp = self.client.embeddings.create(
            model=self.embed_model,
            input=text,
        )
        return resp.data[0].embedding
