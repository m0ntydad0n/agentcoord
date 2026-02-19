import asyncio
import json
from typing import Dict, List, Set, Optional
from datetime import datetime
import logging
from dataclasses import asdict

from .aggregator import ProgressAggregator
from .models import AggregatedProgress, Status

logger = logging.getLogger(__name__)

class ProgressDashboard:
    def __init__(self, aggregator: ProgressAggregator, update_interval: float = 0.5):
        self.aggregator = aggregator
        self.update_interval = update_interval
        self.subscribers: Set[Callable] = set()
        self.last_update: Optional[datetime] = None
        self.cached_status: Dict[str, AggregatedProgress] = {}
        self._update_task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def start(self):
        """Start real-time dashboard updates"""
        if self._update_task and not self._update_task.done():
            return
            
        self._shutdown = False
        self._update_task = asyncio.create_task(self._update_loop())

    async def stop(self):
        """Stop dashboard updates"""
        self._shutdown = True
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

    async def _update_loop(self):
        """Main dashboard update loop"""
        while not self._shutdown:
            try:
                await self._update_dashboard()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating dashboard: {e}")
                await asyncio.sleep(self.update_interval)

    async def _update_dashboard(self):
        """Update dashboard with latest progress data"""
        try:
            current_status = await self.aggregator.get_hierarchy_status()
            
            # Check if there are meaningful changes
            if self._has_significant_changes(current_status):
                self.cached_status = current_status
                self.last_update = datetime.utcnow()
                
                # Notify all subscribers
                dashboard_data = self._format_dashboard_data(current_status)
                await self._notify_subscribers(dashboard_data)
                
        except Exception as e:
            logger.error(f"Failed to update dashboard: {e}")

    def _has_significant_changes(self, new_status: Dict[str, AggregatedProgress]) -> bool:
        """Check if changes are significant enough to warrant an update"""
        if not self.cached_status:
            return True
            
        for node_id, new_progress in new_status.items():
            old_progress = self.cached_status.get(node_id)
            if not old_progress:
                return True
                
            # Check for significant progress changes (>1%)
            if abs(new_progress.weighted_progress - old_progress.weighted_progress) > 1.0:
                return True
                
            # Check for status changes
            if (new_progress.completed_children != old_progress.completed_children or
                new_progress.failed_children != old_progress.failed_children or
                new_progress.bottlenecks != old_progress.bottlenecks):
                return True
                
        return False

    def _format_dashboard_data(self, status: Dict[str, AggregatedProgress]) -> dict:
        """Format progress data for dashboard display"""
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": {},
            "summary": {
                "total_nodes": len(status),
                "overall_progress": 0.0,
                "total_bottlenecks": 0,
                "total_failed": 0
            }
        }

        total_progress = 0.0
        total_bottlenecks = 0
        total_failed = 0

        for node_id, progress in status.items():
            node_data = {
                "node_id": node_id,
                "total_progress": round(progress.total_progress, 2),
                "weighted_progress": round(progress.weighted_progress, 2),
                "child_count": progress.child_count,
                "completed_children": progress.completed_children,
                "failed_children": progress.failed_children,
                "bottlenecks": progress.bottlenecks,
                "status": self._determine_node_status(progress),
                "timestamp": progress.timestamp.isoformat()
            }
            
            dashboard_data["nodes"][node_id] = node_data
            total_progress += progress.weighted_progress
            total_bottlenecks += len(progress.bottlenecks)
            total_failed += progress.failed_children

        # Calculate overall metrics
        if status:
            dashboard_data["summary"]["overall_progress"] = round(
                total_progress / len(status), 2
            )
        dashboard_data["summary"]["total_bottlenecks"] = total_bottlenecks
        dashboard_