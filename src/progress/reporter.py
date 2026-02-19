import asyncio
from typing import Callable, Optional
import logging
from datetime import datetime

from .models import ProgressReport, NodeType, Status
from .aggregator import ProgressAggregator

logger = logging.getLogger(__name__)

class ProgressReporter:
    def __init__(self, node_id: str, node_type: NodeType, 
                 aggregator: ProgressAggregator,
                 report_interval: float = 1.0):
        self.node_id = node_id
        self.node_type = node_type
        self.aggregator = aggregator
        self.report_interval = report_interval
        self.current_status = Status.PENDING
        self.current_progress = 0.0
        self.metadata = {}
        self._reporting_task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def start_reporting(self):
        """Start periodic progress reporting"""
        if self._reporting_task and not self._reporting_task.done():
            return
            
        self._shutdown = False
        self._reporting_task = asyncio.create_task(self._report_loop())

    async def stop_reporting(self):
        """Stop progress reporting"""
        self._shutdown = True
        if self._reporting_task:
            self._reporting_task.cancel()
            try:
                await self._reporting_task
            except asyncio.CancelledError:
                pass

    async def _report_loop(self):
        """Main reporting loop"""
        while not self._shutdown:
            try:
                await self._send_progress_report()
                await asyncio.sleep(self.report_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in progress reporting for {self.node_id}: {e}")
                await asyncio.sleep(self.report_interval)

    async def _send_progress_report(self):
        """Send current progress report"""
        report = ProgressReport(
            node_id=self.node_id,
            node_type=self.node_type,
            status=self.current_status,
            progress_percentage=self.current_progress,
            metadata=self.metadata.copy(),
            timestamp=datetime.utcnow()
        )
        
        await self.aggregator.update_progress(report)

    async def update_progress(self, progress: float, status: Optional[Status] = None,
                            metadata: Optional[dict] = None):
        """Update current progress"""
        self.current_progress = max(0.0, min(100.0, progress))
        
        if status:
            self.current_status = status
            
        if metadata:
            self.metadata.update(metadata)
            
        # Send immediate update for significant changes
        await self._send_progress_report()

    async def mark_completed(self, metadata: Optional[dict] = None):
        """Mark task as completed"""
        await self.update_progress(100.0, Status.COMPLETED, metadata)
        await self.stop_reporting()

    async def mark_failed(self, error: Optional[str] = None):
        """Mark task as failed"""
        metadata = {"error": error} if error else {}
        await self.update_progress(self.current_progress, Status.FAILED, metadata)
        await self.stop_reporting()

    async def mark_blocked(self, reason: Optional[str] = None):
        """Mark task as blocked"""
        metadata = {"blocked_reason": reason} if reason else {}
        await self.update_progress(self.current_progress, Status.BLOCKED, metadata)