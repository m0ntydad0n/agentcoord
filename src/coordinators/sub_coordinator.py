from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from ..models.task import Task, TaskStatus, SubProject
from ..models.worker import Worker, WorkerStatus
from ..communication.message_bus import MessageBus, Message, MessageType
from ..interfaces.coordinator import BaseCoordinator


@dataclass
class TeamMetrics:
    """Metrics for worker team performance"""
    total_workers: int = 0
    active_workers: int = 0
    idle_workers: int = 0
    avg_task_completion_time: float = 0.0
    success_rate: float = 0.0
    current_load: float = 0.0


@dataclass
class StatusReport:
    """Status report for upward communication"""
    coordinator_id: str
    timestamp: datetime
    sub_project_id: str
    progress_percentage: float
    completed_tasks: int
    total_tasks: int
    active_tasks: int
    team_metrics: TeamMetrics
    issues: List[str] = field(default_factory=list)
    resource_requests: List[Dict[str, Any]] = field(default_factory=list)


class SubCoordinator(BaseCoordinator):
    """
    Middle-tier coordinator that manages worker teams and reports to main coordinator
    """
    
    def __init__(
        self,
        coordinator_id: str,
        sub_project: SubProject,
        message_bus: MessageBus,
        max_workers: int = 10,
        report_interval: int = 30
    ):
        self.coordinator_id = coordinator_id
        self.sub_project = sub_project
        self.message_bus = message_bus
        self.max_workers = max_workers
        self.report_interval = report_interval
        
        # Worker management
        self.workers: Dict[str, Worker] = {}
        self.task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []
        
        # Peer coordination
        self.peer_coordinators: Set[str] = set()
        self.shared_resources: Dict[str, Any] = {}
        
        # Status tracking
        self.last_report_time = datetime.now()
        self.metrics = TeamMetrics()
        
        # Concurrency
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        
        self.logger = logging.getLogger(f"SubCoordinator-{coordinator_id}")
        
        # Subscribe to relevant messages
        self._setup_message_handlers()
    
    async def start(self) -> None:
        """Start the sub-coordinator"""
        self.running = True
        self.logger.info(f"Starting SubCoordinator {self.coordinator_id}")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._task_distribution_loop()),
            asyncio.create_task(self._status_reporting_loop()),
            asyncio.create_task(self._health_monitoring_loop()),
            asyncio.create_task(self._message_processing_loop())
        ]
        
        await asyncio.gather(*tasks)
    
    async def stop(self) -> None:
        """Stop the sub-coordinator"""
        self.running = False
        self.logger.info(f"Stopping SubCoordinator {self.coordinator_id}")
        
        # Cleanup workers
        for worker in self.workers.values():
            await worker.stop()
        
        self.executor.shutdown(wait=True)
    
    async def process_sub_project(self, sub_project: SubProject) -> None:
        """Break down sub-project into tasks and manage execution"""
        self.logger.info(f"Processing sub-project: {sub_project.project_id}")
        
        try:
            # Break down sub-project into tasks
            tasks = await self._breakdown_sub_project(sub_project)
            
            # Add tasks to queue
            for task in tasks:
                await self.task_queue.put(task)
            
            self.logger.info(f"Created {len(tasks)} tasks from sub-project {sub_project.project_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing sub-project: {e}")
            await self._report_error(f"Sub-project processing failed: {str(e)}")
    
    async def add_worker(self, worker: Worker) -> bool:
        """Add a worker to the team"""
        if len(self.workers) >= self.max_workers:
            self.logger.warning(f"Cannot add worker {worker.worker_id}: team at capacity")
            return False
        
        self.workers[worker.worker_id] = worker
        await worker.start()
        
        self.logger.info(f"Added worker {worker.worker_id} to team")
        self._update_team_metrics()
        return True
    
    async def remove_worker(self, worker_id: str) -> bool:
        """Remove a worker from the team"""
        if worker_id not in self.workers:
            return False
        
        worker = self.workers.pop(worker_id)
        await worker.stop()
        
        # Reassign any active tasks
        tasks_to_reassign = [
            task for task in self.active_tasks.values()
            if task.assigned_worker_id == worker_id
        ]
        
        for task in tasks_to_reassign:
            task.assigned_worker_id = None
            task.status = TaskStatus.PENDING
            await self.task_queue.put(task)
            del self.active_tasks[task.task_id]
        
        self.logger.info(f"Removed worker {worker_id} and reassigned {len(tasks_to_reassign)} tasks")
        self._update_team_metrics()
        return True
    
    async def request_peer_assistance(self, resource_type: str, requirements: Dict[str, Any]) -> bool:
        """Request assistance from peer coordinators"""
        message = Message(
            message_type=MessageType.RESOURCE_REQUEST,
            sender_id=self.coordinator_id,
            data={
                'resource_type': resource_type,
                'requirements': requirements,
                'coordinator_id': self.coordinator_id
            }
        )
        
        # Broadcast to peer coordinators
        for peer_id in self.peer_coordinators:
            await self.message_bus.send_message(peer_id, message)
        
        self.logger.info(f"Requested {resource_type} assistance from peers")
        return True
    
    async def offer_peer_assistance(self, peer_id: str, resource_type: str, resources: Dict[str, Any]) -> None:
        """Offer assistance to a peer coordinator"""
        message = Message(
            message_type=MessageType.RESOURCE_OFFER,
            sender_id=self.coordinator_id,
            data={
                'resource_type': resource_type,
                'resources': resources,
                'coordinator_id': self.coordinator_id
            }
        )
        
        await self.message_bus.send_message(peer_id, message)
        self.logger.info(f"Offered {resource_type} assistance to {peer_id}")
    
    async def _breakdown_sub_project(self, sub_project: SubProject) -> List[Task]:
        """Break down sub-project into executable tasks"""
        tasks = []
        
        # This is a simplified breakdown - in practice, this would be more sophisticated
        for i, requirement in enumerate(sub_project.requirements):
            task = Task(
                task_id=f"{sub_project.project_id}_task_{i}",
                sub_project_id=sub_project.project_id,
                description=requirement.get('description', ''),
                requirements=requirement,
                priority=requirement.get('priority', 1),
                estimated_duration=requirement.get('estimated_duration', 3600)
            )
            tasks.append(task)
        
        return tasks
    
    async def _task_distribution_loop(self) -> None:
        """Main loop for distributing tasks to workers"""
        while self.running:
            try:
                # Get next task
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # Find available worker
                available_worker = self._find_available_worker(task)
                
                if available_worker:
                    # Assign task
                    task.assigned_worker_id = available_worker.worker_id
                    task.status = TaskStatus.IN_PROGRESS
                    task.start_time = datetime.now()
                    
                    self.active_tasks[task.task_id] = task
                    
                    # Send task to worker
                    await available_worker.assign_task(task)
                    
                    self.logger.debug(f"Assigned task {task.task_id} to worker {available_worker.worker_id}")
                else:
                    # Put task back in queue
                    await self.task_queue.put(task)
                    await asyncio.sleep(1)  # Wait before retrying
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in task distribution: {e}")
    
    async def _status_reporting_loop(self) -> None:
        """Regular status reporting to main coordinator"""
        while self.running:
            try:
                await asyncio.sleep(self.report_interval)
                
                if datetime.now().timestamp() - self.last_report_time.timestamp() >= self.report_interval:
                    await self._send_status_report()
                    
            except Exception as e:
                self.logger.error(f"Error in status reporting: {e}")
    
    async def _health_monitoring_loop(self) -> None:
        """Monitor worker health and system performance"""
        while self.running:
            try:
                # Check worker health
                for worker_id, worker in list(self.workers.items()):
                    if not await worker.is_healthy():
                        self.logger.warning(f"Worker {worker_id} is unhealthy, removing")
                        await self.remove_worker(worker_id)
                
                # Update metrics
                self._update_team_metrics()
                
                # Check for completed tasks
                await self._process_completed_tasks()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring: {e}")
    
    async def _message_processing_loop(self) -> None:
        """Process incoming messages"""
        while self.running:
            try:
                messages = await self.message_bus.receive_messages(self.coordinator_id)
                
                for message in messages:
                    await self._handle_message(message)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                self.logger.error(f"Error processing messages: {e}")
    
    def _find_available_worker(self, task: Task) -> Optional[Worker]:
        """Find an available worker for the task"""
        for worker in self.workers.values():
            if (worker.status == WorkerStatus.IDLE and 
                worker.can_handle_task(task)):
                return worker
        return None
    
    async def _process_completed_tasks(self) -> None:
        """Process completed tasks and update status"""
        completed = []
        
        for task_id, task in self.active_tasks.items():
            worker = self.workers.get(task.assigned_worker_id)
            if worker and await worker.is_task_complete(task_id):
                task.status = TaskStatus.COMPLETED
                task.end_time = datetime.now()
                completed.append(task_id)
                self.completed_tasks.append(task)
                
                self.logger.debug(f"Task {task_id} completed by worker {worker.worker_id}")
        
        # Remove completed tasks from active list
        for task_id in completed:
            del self.active_tasks[task_id]
    
    async def _send_status_report(self) -> None:
        """Send status report to main coordinator"""
        total_tasks = len(self.completed_tasks) + len(self.active_tasks) + self.task_queue.qsize()
        progress = len(self.completed_tasks) / max(total_tasks, 1) * 100
        
        report = StatusReport(
            coordinator_id=self.coordinator_id,
            timestamp=datetime.now(),
            sub_project_id=self.sub_project.project_id,
            progress_percentage=progress,
            completed_tasks=len(self.completed_tasks),
            total_tasks=total_tasks,
            active_tasks=len(self.active_tasks),
            team_metrics=self.metrics
        )
        
        message = Message(
            message_type=MessageType.STATUS_REPORT,
            sender_id=self.coordinator_id,
            data=report.__dict__
        )
        
        await self.message_bus.send_message("main_coordinator", message)
        self.last_report_time = datetime.now()
        
        self.logger.debug(f"Sent status report: {progress:.1f}% complete")
    
    def _update_team_metrics(self) -> None:
        """Update team performance metrics"""
        self.metrics.total_workers = len(self.workers)
        self.metrics.active_workers = sum(1 for w in self.workers.values() if w.status == WorkerStatus.BUSY)
        self.metrics.idle_workers = sum(1 for w in self.workers.values() if w.status == WorkerStatus.IDLE)
        
        if self.completed_tasks:
            completion_times = [
                (task.end_time - task.start_time).total_seconds() 
                for task in self.completed_tasks 
                if task.end_time and task.start_time
            ]
            self.metrics.avg_task_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
            
            successful_tasks = sum(1 for task in self.completed_tasks if task.status == TaskStatus.COMPLETED)
            self.metrics.success_rate = successful_tasks / len(self.completed_tasks)
        
        # Calculate current load
        if self.workers:
            self.metrics.current_load = self.metrics.active_workers / self.metrics.total_workers
    
    async def _handle_message(self, message: Message) -> None:
        """Handle incoming messages"""
        if message.message_type == MessageType.RESOURCE_REQUEST:
            await self._handle_resource_request(message)
        elif message.message_type == MessageType.RESOURCE_OFFER:
            await self._handle_resource_offer(message)
        elif message.message_type == MessageType.TASK_ASSIGNMENT:
            await self._handle_task_assignment(message)
        elif message.message_type == MessageType.PEER_COORDINATION:
            await self._handle_peer_coordination(message)
    
    async def _handle_resource_request(self, message: Message) -> None:
        """Handle resource requests from peers"""
        # Check if we can help
        resource_type = message.data.get('resource_type')
        requirements = message.data.get('requirements', {})
        
        if self._can_provide_resource(resource_type, requirements):
            await self.offer_peer_assistance(
                message.sender_id,
                resource_type,
                self._get_available_resources(resource_type)
            )
    
    async def _handle_resource_offer(self, message: Message) -> None:
        """Handle resource offers from peers"""
        # Accept or decline the offer based on current needs
        resource_type = message.data.get('resource_type')
        resources = message.data.get('resources', {})
        
        # Implementation depends on specific resource needs
        self.logger.info(f"Received resource offer from {message.sender_id}: {resource_type}")
    