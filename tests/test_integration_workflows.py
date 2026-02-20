import pytest
import asyncio
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile
import shutil

from src.core.coordinator import Coordinator
from src.workers.llm_worker import LLMWorker
from src.workers.worker_manager import WorkerManager
from src.core.redis_client import get_redis_client
from src.core.task_queue import TaskQueue
from src.core.audit_logger import AuditLogger


@pytest.fixture
async def redis_client():
    """Redis client with cleanup."""
    client = await get_redis_client()
    
    # Clean up any existing test data
    await client.flushdb()
    
    yield client
    
    # Clean up after test
    await client.flushdb()
    await client.close()


@pytest.fixture
def temp_workspace():
    """Temporary workspace directory."""
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir) / "workspace"
    workspace.mkdir(exist_ok=True)
    
    yield workspace
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API client."""
    with patch('anthropic.AsyncAnthropic') as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.messages.create = AsyncMock()
        
        # Default response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = '''
def hello_world():
    """A simple hello world function."""
    return "Hello, World!"

if __name__ == "__main__":
    print(hello_world())
'''
        mock_instance.messages.create.return_value = mock_response
        
        yield mock_instance


class TestEndToEndWorkflows:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_coordinator_worker_task_lifecycle(self, redis_client, temp_workspace):
        """Test complete task lifecycle: spawn → claim → complete."""
        
        # Setup
        task_queue = TaskQueue(redis_client)
        audit_logger = AuditLogger(redis_client)
        coordinator = Coordinator(redis_client, temp_workspace)
        
        # Create a simple task
        task_data = {
            "id": "test-task-001",
            "type": "code_generation",
            "description": "Create a hello world function",
            "priority": "normal",
            "requirements": {
                "language": "python",
                "output_file": "hello.py"
            }
        }
        
        # Step 1: Coordinator adds task to queue
        await task_queue.add_task(task_data)
        
        # Verify task is queued
        queue_size = await redis_client.llen("task_queue:normal")
        assert queue_size == 1
        
        # Step 2: Mock worker claims task
        claimed_task = await task_queue.claim_task("worker-001")
        assert claimed_task is not None
        assert claimed_task["id"] == "test-task-001"
        
        # Verify task is now in processing state
        processing_tasks = await redis_client.hgetall("tasks:processing")
        assert "test-task-001" in processing_tasks
        
        # Step 3: Mark task as complete
        completion_data = {
            "status": "completed",
            "result": {
                "file_created": str(temp_workspace / "hello.py"),
                "lines_of_code": 5
            },
            "worker_id": "worker-001",
            "execution_time": 2.5
        }
        
        await task_queue.complete_task("test-task-001", completion_data)
        
        # Step 4: Verify cleanup and final state
        # Task should be removed from processing
        processing_tasks = await redis_client.hgetall("tasks:processing")
        assert "test-task-001" not in processing_tasks
        
        # Task should be in completed state
        completed_task = await redis_client.hget("tasks:completed", "test-task-001")
        assert completed_task is not None
        
        completed_data = json.loads(completed_task)
        assert completed_data["status"] == "completed"
        assert completed_data["worker_id"] == "worker-001"
        
        # Audit log should contain entries
        logs = await audit_logger.get_task_logs("test-task-001")
        assert len(logs) >= 3  # queued, claimed, completed
        
        log_actions = [log["action"] for log in logs]
        assert "task_queued" in log_actions
        assert "task_claimed" in log_actions  
        assert "task_completed" in log_actions
    
    @pytest.mark.asyncio
    async def test_llm_worker_execution_workflow(self, redis_client, temp_workspace, mock_anthropic):
        """Test LLM worker executing actual task with mocked API."""
        
        # Setup
        task_queue = TaskQueue(redis_client)
        audit_logger = AuditLogger(redis_client)
        
        # Create LLM worker
        worker = LLMWorker(
            worker_id="llm-worker-001",
            redis_client=redis_client,
            workspace=temp_workspace
        )
        
        # Create a code generation task
        task_data = {
            "id": "llm-task-001",
            "type": "code_generation",
            "description": "Create a Python function that calculates fibonacci numbers",
            "priority": "normal",
            "requirements": {
                "language": "python",
                "output_file": "fibonacci.py",
                "function_name": "fibonacci"
            }
        }
        
        # Add task to queue
        await task_queue.add_task(task_data)
        
        # Configure mock response
        mock_anthropic.messages.create.return_value.content[0].text = '''
def fibonacci(n):
    """Calculate the nth fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Test the function
if __name__ == "__main__":
    for i in range(10):
        print(f"fibonacci({i}) = {fibonacci(i)}")
'''
        
        # Step 1: Worker claims and processes task
        with patch.object(worker, '_make_api_call', return_value=mock_anthropic.messages.create.return_value):
            result = await worker.process_next_task()
        
        # Step 2: Verify task execution
        assert result is not None
        assert result["task_id"] == "llm-task-001"
        assert result["status"] == "completed"
        
        # Step 3: Verify file creation
        output_file = temp_workspace / "fibonacci.py"
        assert output_file.exists()
        
        content = output_file.read_text()
        assert "def fibonacci(n):" in content
        assert "fibonacci number" in content
        
        # Step 4: Verify audit log entries
        logs = await audit_logger.get_task_logs("llm-task-001")
        log_actions = [log["action"] for log in logs]
        
        assert "task_claimed" in log_actions
        assert "llm_api_call" in log_actions
        assert "file_created" in log_actions
        assert "task_completed" in log_actions
        
        # Verify API call was logged
        api_call_log = next((log for log in logs if log["action"] == "llm_api_call"), None)
        assert api_call_log is not None
        assert "model" in api_call_log["details"]
        
        # Step 5: Verify task completion in Redis
        completed_task = await redis_client.hget("tasks:completed", "llm-task-001")
        assert completed_task is not None
        
        completed_data = json.loads(completed_task)
        assert completed_data["result"]["file_created"] == str(output_file)
    
    @pytest.mark.asyncio
    async def test_auto_scaling_workflow(self, redis_client, temp_workspace):
        """Test auto-scaling: queue fills → workers spawn → queue drains → workers terminate."""
        
        # Setup
        task_queue = TaskQueue(redis_client)
        worker_manager = WorkerManager(redis_client, temp_workspace)
        
        # Configure scaling thresholds
        worker_manager.scale_up_threshold = 3
        worker_manager.scale_down_threshold = 1
        worker_manager.max_workers = 5
        worker_manager.min_workers = 1
        
        # Step 1: Fill queue with tasks (above scale-up threshold)
        tasks = []
        for i in range(5):
            task_data = {
                "id": f"scale-task-{i:03d}",
                "type": "code_generation", 
                "description": f"Generate code file {i}",
                "priority": "normal",
                "requirements": {"language": "python", "output_file": f"file_{i}.py"}
            }
            tasks.append(task_data)
            await task_queue.add_task(task_data)
        
        # Verify queue is filled
        queue_size = await redis_client.llen("task_queue:normal")
        assert queue_size == 5
        
        # Step 2: Trigger scaling check - should scale up
        initial_worker_count = await worker_manager.get_active_worker_count()
        
        scale_decision = await worker_manager.should_scale()
        assert scale_decision["action"] == "scale_up"
        assert scale_decision["target_workers"] > initial_worker_count
        
        # Mock worker spawning
        with patch.object(worker_manager, '_spawn_worker') as mock_spawn:
            mock_spawn.return_value = {"worker_id": "auto-worker-001", "pid": 12345}
            
            await worker_manager.scale_workers()
            
            # Verify workers were spawned
            assert mock_spawn.call_count > 0
        
        # Step 3: Simulate task processing (drain queue)
        # Mock workers claiming and completing tasks
        for i in range(4):  # Leave 1 task
            claimed_task = await task_queue.claim_task(f"worker-{i}")
            if claimed_task:
                await task_queue.complete_task(
                    claimed_task["id"], 
                    {"status": "completed", "worker_id": f"worker-{i}"}
                )
        
        # Verify queue drained
        queue_size = await redis_client.llen("task_queue:normal")
        assert queue_size == 1  # Only 1 task left
        
        # Step 4: Trigger scaling check - should scale down
        scale_decision = await worker_manager.should_scale()
        assert scale_decision["action"] in ["scale_down", "maintain"]  # Depends on current worker count
        
        # Step 5: Verify worker count management
        # Test scaling limits
        await worker_manager._update_worker_count(10)  # Above max
        worker_count = await worker_manager.get_active_worker_count()
        assert worker_count <= worker_manager.max_workers
        
        await worker_manager._update_worker_count(0)  # Below min
        worker_count = await worker_manager.get_active_worker_count()
        assert worker_count >= worker_manager.min_workers
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, redis_client, temp_workspace):
        """Test error scenarios and recovery mechanisms."""
        
        task_queue = TaskQueue(redis_client)
        audit_logger = AuditLogger(redis_client)
        
        # Create a task that will fail
        task_data = {
            "id": "error-task-001",
            "type": "code_generation",
            "description": "This task will fail",
            "priority": "normal",
            "requirements": {"language": "python", "output_file": "error.py"}
        }
        
        await task_queue.add_task(task_data)
        
        # Simulate task failure
        claimed_task = await task_queue.claim_task("error-worker")
        assert claimed_task is not None
        
        # Mark task as failed
        failure_data = {
            "status": "failed",
            "error": "Simulated API error",
            "worker_id": "error-worker",
            "retry_count": 1
        }
        
        await task_queue.fail_task("error-task-001", failure_data)
        
        # Verify task moved to failed state
        failed_task = await redis_client.hget("tasks:failed", "error-task-001")
        assert failed_task is not None
        
        failed_data = json.loads(failed_task)
        assert failed_data["status"] == "failed"
        assert "Simulated API error" in failed_data["error"]
        
        # Verify audit logging
        logs = await audit_logger.get_task_logs("error-task-001")
        log_actions = [log["action"] for log in logs]
        assert "task_failed" in log_actions
        
        # Test task retry
        await task_queue.retry_task("error-task-001")
        
        # Task should be back in queue
        queue_size = await redis_client.llen("task_queue:normal")
        assert queue_size >= 1
    
    @pytest.mark.asyncio
    async def test_concurrent_worker_processing(self, redis_client, temp_workspace, mock_anthropic):
        """Test multiple workers processing tasks concurrently."""
        
        task_queue = TaskQueue(redis_client)
        
        # Create multiple tasks
        tasks = []
        for i in range(6):
            task_data = {
                "id": f"concurrent-task-{i:03d}",
                "type": "code_generation",
                "description": f"Generate concurrent code {i}",
                "priority": "normal",
                "requirements": {"language": "python", "output_file": f"concurrent_{i}.py"}
            }
            tasks.append(task_data)
            await task_queue.add_task(task_data)
        
        # Create multiple workers
        workers = []
        for i in range(3):
            worker = LLMWorker(
                worker_id=f"concurrent-worker-{i:03d}",
                redis_client=redis_client,
                workspace=temp_workspace
            )
            workers.append(worker)
        
        # Process tasks concurrently
        async def process_worker_tasks(worker):
            results = []
            for _ in range(3):  # Each worker processes up to 3 tasks
                with patch.object(worker, '_make_api_call', return_value=mock_anthropic.messages.create.return_value):
                    result = await worker.process_next_task()
                    if result:
                        results.append(result)
                    await asyncio.sleep(0.1)  # Small delay to simulate processing
            return results
        
        # Run workers concurrently
        worker_results = await asyncio.gather(*[
            process_worker_tasks(worker) for worker in workers
        ])
        
        # Verify results
        total_processed = sum(len(results) for results in worker_results)
        assert total_processed == 6  # All tasks should be processed
        
        # Verify no duplicate processing
        processed_task_ids = set()
        for results in worker_results:
            for result in results:
                task_id = result["task_id"]
                assert task_id not in processed_task_ids  # No duplicates
                processed_task_ids.add(task_id)
        
        # Verify all tasks completed
        for i in range(6):
            task_id = f"concurrent-task-{i:03d}"
            completed_task =