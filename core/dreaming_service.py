"""
DreamingService — 记忆压缩核心服务

基于 Embedding 聚类的离线记忆巩固：
1. 选择待处理记忆
2. Embedding 聚类
3. 簇内合并
4. 归档原始记忆
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from .database import Database
from .ai_compressor import AiCompressor
from .models import Note

# 默认阈值来自 5.0 验证实验结果
DEFAULT_THRESHOLD = 0.70
CONSERVATIVE_THRESHOLD = 0.75
AGGRESSIVE_THRESHOLD = 0.65

MODEL_NAME = "shibing624/text2vec-base-chinese"


class DreamingService:
    """记忆 Dreaming 服务"""

    def __init__(self, db: Database):
        self.db = db
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self) -> SentenceTransformer:
        # 策略 1：离线模式（模型已缓存）
        cache_dir = os.path.expanduser(
            "~/.cache/huggingface/hub/models--shibing624--text2vec-base-chinese")
        if os.path.isdir(cache_dir):
            try:
                return SentenceTransformer(MODEL_NAME, local_files_only=True)
            except Exception:
                pass

        # 策略 2：HuggingFace 镜像（国内网络）
        try:
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            return SentenceTransformer(MODEL_NAME)
        except Exception:
            pass

        # 策略 3：直连
        os.environ.pop("HF_ENDPOINT", None)
        return SentenceTransformer(MODEL_NAME)

    # ── Step 1: 选择记忆 ──────────────────────────────────

    def select_memories_for_dreaming(
        self,
        workspace_id: Optional[int] = None,
        strategy: str = "default",
        min_age_days: int = 7
    ) -> list[Note]:
        """选择适合 Dreaming 的记忆

        Args:
            workspace_id: 工作区过滤
            strategy: 'default' | 'aggressive' | 'conservative'
            min_age_days: 最小创建天数 (default 模式下生效)

        Returns:
            符合策略的笔记列表
        """
        if strategy == "aggressive":
            return self._get_all_notes(workspace_id)

        if strategy == "conservative":
            min_age_days = 30

        cutoff = datetime.now() - timedelta(days=min_age_days)
        has_ws = self._has_column('notes', 'workspace_id')

        if workspace_id and has_ws:
            cursor = self.db.execute(
                "SELECT id, title, content, tags, created_at, updated_at "
                "FROM notes WHERE created_at <= ? AND workspace_id = ? "
                "ORDER BY created_at",
                (cutoff.isoformat(), workspace_id)
            )
        else:
            cursor = self.db.execute(
                "SELECT id, title, content, tags, created_at, updated_at "
                "FROM notes WHERE created_at <= ? ORDER BY created_at",
                (cutoff.isoformat(),)
            )

        return [Note.from_row(row) for row in cursor.fetchall()]

    def _get_all_notes(self, workspace_id: Optional[int] = None) -> list[Note]:
        has_ws = self._has_column('notes', 'workspace_id')
        if workspace_id and has_ws:
            cursor = self.db.execute(
                "SELECT id, title, content, tags, created_at, updated_at "
                "FROM notes WHERE workspace_id = ?",
                (workspace_id,)
            )
        else:
            cursor = self.db.execute(
                "SELECT id, title, content, tags, created_at, updated_at FROM notes"
            )
        return [Note.from_row(row) for row in cursor.fetchall()]

    # ── Step 2: 聚类 ──────────────────────────────────────

    def cluster_memories(
        self,
        notes: list[Note],
        threshold: float = DEFAULT_THRESHOLD
    ) -> list[list[Note]]:
        """基于 Embedding + 余弦相似度的贪心聚类

        Args:
            notes: 笔记列表
            threshold: 相似度阈值

        Returns:
            聚类结果（每元素为一个簇的笔记列表）
        """
        if len(notes) <= 1:
            return [[n] for n in notes]

        texts = [f"{n.title} {n.content}" for n in notes]
        embeddings = self.model.encode(texts, show_progress_bar=False)

        return self._greedy_cluster(notes, embeddings, threshold)

    def _greedy_cluster(
        self,
        notes: list[Note],
        embeddings: np.ndarray,
        threshold: float
    ) -> list[list[Note]]:
        n = len(notes)
        assigned = [False] * n
        clusters = []

        for i in range(n):
            if assigned[i]:
                continue
            cluster = [notes[i]]
            assigned[i] = True
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                # 与簇内所有已分配项比较
                sims = [
                    float(np.dot(embeddings[j], embeddings[idx]) /
                          (np.linalg.norm(embeddings[j]) *
                           np.linalg.norm(embeddings[idx])))
                    for idx in [notes.index(c) for c in cluster]
                ]
                if all(s >= threshold for s in sims):
                    cluster.append(notes[j])
                    assigned[j] = True
            clusters.append(cluster)

        return clusters

    # ── Step 3: 合并 ──────────────────────────────────────

    def merge_cluster(
        self,
        cluster: list[Note],
        workspace_id: Optional[int] = None,
        session_id: Optional[int] = None
    ) -> Note:
        """合并一个记忆簇为单条记忆

        策略：取第一条的标题，合并所有内容，合并标签并集。

        Args:
            cluster: 待合并的笔记簇
            workspace_id: 工作区 ID
            session_id: Dreaming 会话 ID

        Returns:
            合并后的笔记
        """
        if len(cluster) == 1:
            return cluster[0]

        # 标题：取最具代表性的（第一条）
        title = f"{cluster[0].title} (已合并{len(cluster)}条)"

        # 内容：合并所有内容
        parts = []
        for i, note in enumerate(cluster):
            parts.append(f"## 原笔记 {i + 1}: {note.title}\n{note.content}\n")
        content = "\n".join(parts)

        # 标签：合并去重
        all_tags = set()
        for note in cluster:
            if note.tags:
                try:
                    tag_list = (json.loads(note.tags)
                                if isinstance(note.tags, str) else note.tags)
                    all_tags.update(tag_list)
                except (json.JSONDecodeError, TypeError):
                    pass
        tags = json.dumps(sorted(all_tags), ensure_ascii=False)

        # 写入合并后的笔记
        has_ws = self._has_column('notes', 'workspace_id')
        if workspace_id and has_ws:
            cursor = self.db.execute(
                "INSERT INTO notes (title, content, tags, workspace_id) VALUES (?, ?, ?, ?)",
                (title, content, tags, workspace_id)
            )
        else:
            cursor = self.db.execute(
                "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                (title, content, tags)
            )
        self.db.commit()
        merged_id = cursor.lastrowid

        # 归档原始笔记 + 记录变更
        source_ids = [n.id for n in cluster]
        for nid in source_ids:
            self.db.execute(
                "UPDATE notes SET content = content || ? WHERE id = ?",
                (f"\n\n[归档于 Dreaming: 已合并到 note#{merged_id}]", nid)
            )
        self.db.commit()

        if session_id:
            self._record_change(session_id, "merge", source_ids, merged_id,
                                f"合并{len(cluster)}条: {cluster[0].title}")

        return Note(
            id=merged_id,
            title=title,
            content=content,
            tags=tags,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

    # ── Step 4 & 5: Pipeline ──────────────────────────────

    def run_dreaming(
        self,
        workspace_id: Optional[int] = None,
        strategy: str = "default",
        threshold: float = DEFAULT_THRESHOLD,
        dry_run: bool = False,
        ai_compress: bool = False,
    ) -> dict:
        """运行完整 Dreaming 管线

        Args:
            workspace_id: 工作区过滤
            strategy: 记忆选择策略
            threshold: 聚类阈值
            dry_run: True 时只返回报告，不写入数据库
            ai_compress: 启用 AI 压缩（需要 DeepSeek API）

        Returns:
            报告 dict
        """
        notes = self.select_memories_for_dreaming(
            workspace_id=workspace_id, strategy=strategy)

        input_count = len(notes)

        if input_count < 2:
            return {
                'session_id': None,
                'input_count': input_count,
                'output_count': input_count,
                'merged_count': 0,
                'archived_count': 0,
                'extracted_facts': 0,
                'dry_run': dry_run,
                'clusters': [],
            }

        clusters = self.cluster_memories(notes, threshold=threshold)

        # 单元素簇不合并
        multi_clusters = [c for c in clusters if len(c) > 1]

        if dry_run:
            return {
                'session_id': None,
                'input_count': input_count,
                'output_count': len(clusters),
                'merged_count': sum(len(c) for c in multi_clusters),
                'archived_count': sum(len(c) for c in multi_clusters),
                'extracted_facts': 0,
                'dry_run': True,
                'clusters': [[n.id for n in c] for c in clusters if len(c) > 1],
            }

        # 创建 session
        cursor = self.db.execute(
            "INSERT INTO dreaming_sessions (trigger, status, input_count) VALUES (?, 'running', ?)",
            (strategy, input_count)
        )
        self.db.commit()
        session_id = cursor.lastrowid

        merged_count = 0
        archived_count = 0
        output_notes = []

        try:
            for cluster in multi_clusters:
                merged_note = self.merge_cluster(
                    cluster, workspace_id=workspace_id, session_id=session_id
                )
                output_notes.append(merged_note)
                merged_count += len(cluster)
                archived_count += len(cluster)

            # AI 压缩
            concentrates = []
            if ai_compress and multi_clusters:
                api_key = (os.getenv("DEEPSEEK_API_KEY") or
                           os.getenv("AI_COMPRESS_API_KEY") or "")
                if api_key:
                    compressor = AiCompressor(api_key=api_key)
                    total_tokens = 0
                    for cluster in multi_clusters:
                        cluster_notes = [n for n in notes if n.id in {n.id for n in cluster}]
                        if not cluster_notes:
                            cluster_notes = cluster
                        result = compressor.compress_cluster(cluster_notes)
                        total_tokens += result.token_usage

                        # 找到对应的 merged_note
                        merged = next(
                            (m for m in output_notes if m.id and
                             any(n.id for n in cluster)),
                            None
                        )
                        if merged:
                            self.db.execute(
                                """INSERT INTO dreaming_concentrates
                                   (session_id, source_ids, target_note_id,
                                    ai_title, ai_content, keywords)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (session_id, json.dumps([n.id for n in cluster]),
                                 merged.id, result.title, result.content,
                                 json.dumps(result.keywords, ensure_ascii=False))
                            )
                            concentrates.append({
                                "source_ids": [n.id for n in cluster],
                                "target_note_id": merged.id,
                                "ai_title": result.title,
                                "ai_content": result.content[:200],
                                "keywords": result.keywords,
                            })
                    self.db.commit()
                    # 更新 session 的 ai 字段
                    self.db.execute(
                        "UPDATE dreaming_sessions SET ai_compressed=1, token_cost=? WHERE id=?",
                        (total_tokens, session_id)
                    )
                    self.db.commit()

            # 计算输出数：保留的单元素 + 合并后的
            singleton_count = sum(1 for c in clusters if len(c) == 1)
            output_count = singleton_count + len(multi_clusters)

            # 更新 session
            self.db.execute(
                "UPDATE dreaming_sessions SET status='completed', "
                "finished_at=?, output_count=?, merged_count=?, archived_count=? "
                "WHERE id=?",
                (datetime.now().isoformat(), output_count,
                 merged_count, archived_count, session_id)
            )
            self.db.commit()

        except Exception as e:
            self.db.execute(
                "UPDATE dreaming_sessions SET status='failed', error_message=? WHERE id=?",
                (str(e), session_id)
            )
            self.db.commit()
            raise
        return {
            'session_id': session_id,
            'status': 'ok',
            'input_count': input_count,
            'output_count': output_count,
            'merged_count': merged_count,
            'archived_count': archived_count,
            'extracted_facts': 0,
            'dry_run': False,
            'clusters': [[n.id for n in c] for c in clusters if len(c) > 1],
            'concentrates': concentrates if ai_compress and multi_clusters else [],
            'ai_compressed': bool(ai_compress and multi_clusters and api_key),
        }

    # ── 回滚 ─────────────────────────────────────────────

    def rollback(self, session_id: int) -> dict:
        """回滚一次 Dreaming 会话

        恢复被归档的原始笔记，删除合并产生的笔记。

        Args:
            session_id: Dreaming 会话 ID

        Returns:
            回滚结果
        """
        # 标记 session 为回滚
        self.db.execute(
            "UPDATE dreaming_sessions SET status='rolled_back' WHERE id=?",
            (session_id,)
        )

        # 获取所有 merge 变更
        cursor = self.db.execute(
            "SELECT * FROM dreaming_changes WHERE session_id=? AND change_type='merge'",
            (session_id,)
        )
        changes = cursor.fetchall()

        restored = 0
        deleted = 0

        for row in changes:
            source_ids = json.loads(row['source_ids'])
            target_id = row['target_id']

            # 恢复原始笔记（去掉归档标记）
            for nid in source_ids:
                cursor2 = self.db.execute(
                    "SELECT content FROM notes WHERE id=?", (nid,)
                )
                note_row = cursor2.fetchone()
                if note_row:
                    content = note_row['content']
                    # 移除归档标记
                    cleaned = content.split("\n\n[归档于 Dreaming:")[0]
                    self.db.execute(
                        "UPDATE notes SET content=? WHERE id=?",
                        (cleaned, nid)
                    )
                    restored += 1

            # 删除合并产生的笔记
            if target_id:
                self.db.execute("DELETE FROM notes WHERE id=?", (target_id,))
                self.db.execute("DELETE FROM notes_fts WHERE rowid=?", (target_id,))
                deleted += 1

        self.db.commit()

        return {
            'session_id': session_id,
            'restored_notes': restored,
            'deleted_merged_notes': deleted,
            'changes_reverted': len(changes),
        }

    # ── 历史查询 ─────────────────────────────────────────

    def get_history(self, limit: int = 20) -> list[dict]:
        """获取 Dreaming 历史"""
        cursor = self.db.execute(
            "SELECT * FROM dreaming_sessions ORDER BY started_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_changes(self, session_id: int) -> list[dict]:
        """获取指定 session 的变更记录"""
        cursor = self.db.execute(
            "SELECT * FROM dreaming_changes WHERE session_id=? ORDER BY id",
            (session_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ── 辅助 ──────────────────────────────────────────────

    def _record_change(self, session_id: int, change_type: str,
                       source_ids: list[int], target_id: Optional[int],
                       summary: str):
        self.db.execute(
            "INSERT INTO dreaming_changes (session_id, change_type, source_ids, "
            "target_id, diff_summary) VALUES (?, ?, ?, ?, ?)",
            (session_id, change_type, json.dumps(source_ids), target_id, summary)
        )
        self.db.commit()

    def _has_column(self, table: str, column: str) -> bool:
        try:
            cursor = self.db.execute(f"PRAGMA table_info({table})")
            return column in [r['name'] for r in cursor.fetchall()]
        except Exception:
            return False
