"""
DreamingScheduler — 定时触发 Dreaming

通过后台线程实现每日定时记忆整理。
通过环境变量 MEMOMIND_SCHEDULE=1 启用。
"""
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

from .dreaming_service import DreamingService

logger = logging.getLogger(__name__)


class DreamingScheduler:
    """Dreaming 定时调度器"""

    def __init__(self, dreaming: DreamingService, strategy: str = "default",
                 min_notes: int = 50, min_days: int = 7):
        self.dreaming = dreaming
        self.strategy = strategy
        self.min_notes = min_notes
        self.min_days = min_days
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def start(self, target_hour: int = 3):
        """启动定时调度

        Args:
            target_hour: 每日触发时间（24 小时制，默认凌晨 3 点）
        """
        if self._running:
            return
        self._running = True
        self._schedule_next(target_hour)

    def _schedule_next(self, target_hour: int):
        """计算距离下一次触发的秒数并设置定时器"""
        now = datetime.now()
        next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

        delay = (next_run - now).total_seconds()
        logger.info("DreamingScheduler: 下次触发时间 %s (%.1f 小时后)",
                     next_run.strftime("%Y-%m-%d %H:%M:%S"), delay / 3600)

        self._timer = threading.Timer(delay, self._on_tick, args=[target_hour])
        self._timer.daemon = True
        self._timer.start()

    def _on_tick(self, target_hour: int):
        """定时器回调"""
        try:
            if self.should_dreaming():
                logger.info("DreamingScheduler: 开始定时 Dreaming (strategy=%s)", self.strategy)
                report = self.dreaming.run_dreaming(strategy=self.strategy)
                logger.info(
                    "DreamingScheduler: 完成 — 输入 %d, 输出 %d, 合并 %d",
                    report["input_count"], report["output_count"], report["merged_count"]
                )
            else:
                logger.info("DreamingScheduler: 未达阈值，跳过本次 Dreaming")
        except Exception as e:
            logger.error("DreamingScheduler: 执行失败 — %s", e)

        # 调度下一次
        if self._running:
            self._schedule_next(target_hour)

    def should_dreaming(self) -> bool:
        """判断是否该触发 Dreaming（阈值触发）

        两个条件同时满足才触发：
        1. 活跃笔记数 >= min_notes
        2. 距上次 Dreaming >= min_days 天（或从未 Dream 过）
        """
        # 1. 记忆数阈值
        cursor = self.dreaming.db.execute(
            "SELECT COUNT(*) FROM notes WHERE is_archived = 0"
        )
        note_count = cursor.fetchone()[0]
        if note_count < self.min_notes:
            return False

        # 2. 距上次 Dreaming 时间
        cursor = self.dreaming.db.execute(
            "SELECT finished_at FROM dreaming_sessions "
            "WHERE status = 'completed' ORDER BY finished_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row and row['finished_at']:
            last = datetime.fromisoformat(row['finished_at'])
            if (datetime.now() - last).days < self.min_days:
                return False

        return True

    def stop(self):
        """停止调度"""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("DreamingScheduler: 已停止")

    def run_now(self) -> dict:
        """立即执行一次 Dreaming（不阻塞）"""
        logger.info("DreamingScheduler: 手动触发")
        return self.dreaming.run_dreaming(strategy=self.strategy)
