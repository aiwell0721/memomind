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

    def __init__(self, dreaming: DreamingService, strategy: str = "default"):
        self.dreaming = dreaming
        self.strategy = strategy
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
            logger.info("DreamingScheduler: 开始定时 Dreaming (strategy=%s)", self.strategy)
            report = self.dreaming.run_dreaming(strategy=self.strategy)
            logger.info(
                "DreamingScheduler: 完成 — 输入 %d, 输出 %d, 合并 %d",
                report["input_count"], report["output_count"], report["merged_count"]
            )
        except Exception as e:
            logger.error("DreamingScheduler: 执行失败 — %s", e)

        # 调度下一次
        if self._running:
            self._schedule_next(target_hour)

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
