"""
AI 压缩器 — 调用 DeepSeek 对笔记簇进行智能浓缩

自动降级：API 失败时返回拼接结果，不阻塞流程。
"""

import json
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CompressResult:
    """AI 压缩结果"""
    title: str
    content: str
    keywords: list[str] = field(default_factory=list)
    token_usage: int = 0


class AiCompressor:
    """AI 压缩器：调用 DeepSeek 对笔记簇进行智能浓缩"""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-v4-flash",
        max_input_tokens: int = 8000,
        base_url: str = "https://api.deepseek.com/chat/completions",
    ):
        self.api_key = api_key
        self.model = model
        self.max_input_tokens = max_input_tokens
        self.base_url = base_url

    def compress_cluster(self, notes: list) -> CompressResult:
        """压缩一个笔记簇，返回结构化结果

        自动处理：格式异常降级、超时降级、重试。
        """
        if not notes:
            return CompressResult(title="", content="", keywords=[], token_usage=0)

        # 构建提示词
        truncated = [self._truncate_content(n, self.max_input_tokens // max(len(notes), 1)) for n in notes]
        prompt = self._build_prompt(truncated)

        # 调用 LLM（含重试）
        last_error = None
        for attempt in range(2):  # 最多重试 1 次
            try:
                raw = self._call_llm(prompt)
                result = self._parse_response(raw, notes)
                if result:
                    return result
            except (TimeoutError, RuntimeError) as e:
                logger.warning(f"AI compress attempt {attempt + 1} failed: {e}")
                last_error = e

        # 降级：简单拼接
        logger.info(f"AI compress failed after retries, falling back to simple merge. Last error: {last_error}")
        return self._fallback(notes)

    def _build_prompt(self, notes: list) -> list[dict]:
        """构建 LLM 消息"""
        system = {
            "role": "system",
            "content": (
                "你是一个知识压缩助手。你的任务是将多篇内容相似的笔记合并为一篇精简的知识点。\n"
                "要求：\n"
                "1. 去除重复信息，保留关键技术决策、架构选型、数据和结论\n"
                "2. 保持可读性，使用中文\n"
                "3. 不要添加原文中没有的新信息\n"
                "4. 输出格式必须为："
                "第一行 [标题]\n第二行 标题内容\n"
                "第三行 [精要]\n后面是精简内容\n"
                "最后一行 [关键词]\n后面是逗号分隔的关键词"
            ),
        }

        parts = []
        for n in notes:
            title = getattr(n, "title", "未命名")
            content = getattr(n, "content", "")
            parts.append(f"## {title}\n{content}\n")

        user = {
            "role": "user",
            "content": "以下是内容相似的笔记：\n\n" + "\n".join(parts) + "\n请按格式输出：",
        }

        return [system, user]

    def _call_llm(self, messages: list[dict]) -> str:
        """调用 DeepSeek API"""
        import urllib.request
        import urllib.error

        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.3,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.base_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                raise RuntimeError(f"API response missing choices: {data}")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}")
        except urllib.error.URLError as e:
            raise TimeoutError(f"Network error: {e.reason}")

    def _parse_response(self, raw: str, notes: list) -> Optional[CompressResult]:
        """解析 LLM 返回的结构化文本"""
        if not raw:
            return None

        title = ""
        content = ""
        keywords = []

        # 尝试正则提取
        title_match = re.search(r"\[标题\]\s*\n(.+)", raw)
        if title_match:
            title = title_match.group(1).strip()

        content_match = re.search(r"\[精要\]\s*\n(.+?)(?=\n\[关键词\]|\Z)", raw, re.DOTALL)
        if content_match:
            content = content_match.group(1).strip()

        kw_match = re.search(r"\[关键词\]\s*\n(.+)", raw)
        if kw_match:
            raw_kw = kw_match.group(1).strip()
            keywords = [k.strip() for k in re.split(r"[，,、]+", raw_kw) if k.strip()]

        # 如果格式不对，返回 None 触发降级
        if not title and not content:
            return None

        # 标题/内容为空时用兜底
        if not title:
            title = getattr(notes[0], "title", "合并笔记") if notes else "合并笔记"
        if not content:
            content = raw[:500]
        if not keywords:
            keywords_set = set()
            for n in notes:
                try:
                    tags = json.loads(getattr(n, "tags", "[]"))
                    if isinstance(tags, list):
                        keywords_set.update(tags)
                except (json.JSONDecodeError, TypeError):
                    pass
            keywords = sorted(keywords_set)

        return CompressResult(
            title=title,
            content=content,
            keywords=keywords,
            token_usage=len(raw) // 2,  # 粗略估算
        )

    def _fallback(self, notes: list) -> CompressResult:
        """降级：简单拼接"""
        title = f"{getattr(notes[0], 'title', '合并')} (已合并{len(notes)}条)"
        parts = []
        keywords_set = set()
        for n in notes:
            parts.append(f"## {getattr(n, 'title', '未命名')}\n{getattr(n, 'content', '')}\n")
            try:
                tags = json.loads(getattr(n, "tags", "[]"))
                if isinstance(tags, list):
                    keywords_set.update(tags)
            except (json.JSONDecodeError, TypeError):
                pass

        return CompressResult(
            title=title,
            content="\n".join(parts),
            keywords=sorted(keywords_set),
            token_usage=0,
        )

    def _truncate_content(self, note, max_chars: int) -> type("Note", (), {}):
        """截断过长的笔记内容"""
        content = getattr(note, "content", "")
        if len(content) > max_chars:
            half = max_chars // 2
            content = content[:half] + "\n...(中间省略)...\n" + content[-half:]
        # 返回一个兼容 Note 的对象
        return type("Note", (), {
            "id": getattr(note, "id", 0),
            "title": getattr(note, "title", ""),
            "content": content,
            "tags": getattr(note, "tags", "[]"),
        })
