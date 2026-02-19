import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging

from .models import ProgressReport, AggregatedProgress, NodeType, Status

logger = logging.getLogger(__name__)

class ProgressAggregator:
    def __init__(self, bottleneck_threshold: float = 0.1):
        self.progress_reports: Dict[str, ProgressReport] = {}
        self.hierarchy: Dict[str, List[str]] = defaultdict(list)  # parent -> children
        self.parent_map: Dict[str, str] = {}  # child -> parent
        self.weights: Dict[str, float] = defaultdict(lambda: 1.0)
        self.bottleneck_threshold = bottleneck_threshold
        self._lock = asyncio.Lock()

    async def register_node(self, node_id: str, parent_id: Optional[str] = None, 
                           weight: float = 1.0):
        """Register a node in the hierarchy"""
        async with self._lock:
            if parent_id:
                self.hierarchy[parent_id].append(node_id)
                self.parent_map[node_id] = parent_id
            self.weights[node_id] = weight

    async def update_progress(self, report: ProgressReport) -> Optional[AggregatedProgress]:
        """Update progress for a node and propagate up the hierarchy"""
        async with self._lock:
            self.progress_reports[report.node_id] = report
            
            # If this is a worker node, propagate up
            if report.node_id in self.parent_map:
                parent_id = self.parent_map[report.node_id]
                return await self._aggregate_progress(parent_id)
            
            return None

    async def _aggregate_progress(self, node_id: str) -> AggregatedProgress:
        """Aggregate progress from child nodes"""
        children = self.hierarchy[node_id]
        if not children:
            # Leaf node, return its own progress
            report = self.progress_reports.get(node_id)
            if report:
                return AggregatedProgress(
                    node_id=node_id,
                    total_progress=report.progress_percentage,
                    weighted_progress=report.progress_percentage,
                    child_count=0,
                    completed_children=1 if report.status == Status.COMPLETED else 0,
                    failed_children=1 if report.status == Status.FAILED else 0
                )

        total_weight = sum(self.weights[child] for child in children)
        weighted_progress = 0.0
        completed_count = 0
        failed_count = 0
        bottlenecks = []

        child_progresses = []
        
        for child_id in children:
            child_report = self.progress_reports.get(child_id)
            if child_report:
                child_weight = self.weights[child_id]
                child_progress = child_report.progress_percentage
                
                # Calculate weighted contribution
                weight_ratio = child_weight / total_weight if total_weight > 0 else 0
                weighted_progress += child_progress * weight_ratio
                
                child_progresses.append((child_id, child_progress, child_report))
                
                if child_report.status == Status.COMPLETED:
                    completed_count += 1
                elif child_report.status == Status.FAILED:
                    failed_count += 1

        # Detect bottlenecks
        bottlenecks = self._detect_bottlenecks(child_progresses)
        
        aggregated = AggregatedProgress(
            node_id=node_id,
            total_progress=sum(p[1] for p in child_progresses) / len(child_progresses) if child_progresses else 0,
            weighted_progress=weighted_progress,
            child_count=len(children),
            completed_children=completed_count,
            failed_children=failed_count,
            bottlenecks=bottlenecks
        )

        # Propagate further up if this node has a parent
        if node_id in self.parent_map:
            parent_id = self.parent_map[node_id]
            # Create synthetic report for this aggregated node
            synthetic_report = ProgressReport(
                node_id=node_id,
                node_type=NodeType.SUB_COORDINATOR,
                status=Status.COMPLETED if completed_count == len(children) else 
                       Status.FAILED if failed_count > 0 else Status.RUNNING,
                progress_percentage=weighted_progress,
                weight=self.weights[node_id]
            )
            self.progress_reports[node_id] = synthetic_report
            await self._aggregate_progress(parent_id)

        return aggregated

    def _detect_bottlenecks(self, child_progresses: List[tuple]) -> List[str]:
        """Identify nodes that are significantly behind others"""
        if len(child_progresses) < 2:
            return []

        bottlenecks = []
        progresses = [p[1] for p in child_progresses]
        avg_progress = sum(progresses) / len(progresses)
        
        for child_id, progress, report in child_progresses:
            if (avg_progress - progress) > self.bottleneck_threshold * 100:
                # Additional checks for bottleneck conditions
                if (report.status in [Status.BLOCKED, Status.FAILED] or 
                    (report.throughput and report.throughput < 0.1)):  # Very low throughput
                    bottlenecks.append(child_id)

        return bottlenecks

    async def get_aggregated_progress(self, node_id: str) -> Optional[AggregatedProgress]:
        """Get current aggregated progress for a node"""
        async with self._lock:
            return await self._aggregate_progress(node_id)

    async def get_hierarchy_status(self) -> Dict[str, AggregatedProgress]:
        """Get status for entire hierarchy"""
        async with self._lock:
            result = {}
            # Get all parent nodes (nodes that have children)
            for parent_id in self.hierarchy.keys():
                result[parent_id] = await self._aggregate_progress(parent_id)
            return result