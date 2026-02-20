import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from agentcoord.tasks import Task, TaskQueue


class TestTask:
    def test_task_creation_minimal(self):
        """Test creating a task with minimal parameters"""
        task = Task("test-task", "echo hello")
        assert task.id == "test-task"
        assert task.command == "echo hello"
        assert task.status == "pending"
        assert task.priority == 0
        assert task.tags == []
        assert task.max_retries == 3
        assert task.retry_count == 0

    def test_task_creation_full_parameters(self):
        """Test creating a task with all parameters"""
        task = Task(
            id="full-task",
            command="python script.py",
            priority=5,
            tags=["important", "batch"],
            max_retries=5,
            working_dir="/tmp",
            env_vars={"KEY": "value"},
            timeout=300
        )
        assert task.id == "full-task"
        assert task.command == "python script.py"
        assert task.priority == 5
        assert task.tags == ["important", "batch"]
        assert task.max_retries == 5
        assert task.working_dir == "/tmp"
        assert task.env_vars == {"KEY": "value"}
        assert task.timeout == 300

    def test_task_to_dict(self):
        """Test task serialization to dictionary"""
        task = Task("test", "echo test", priority=1, tags=["tag1"])
        task_dict = task.to_dict()
        
        expected_keys = {"id", "command", "status", "priority", "tags", 
                        "max_retries", "retry_count", "working_dir", 
                        "env_vars", "timeout", "created_at", "started_at", 
                        "completed_at", "result", "error"}
        assert set(task_dict.keys()) == expected_keys

    def test_task_from_dict(self):
        """Test task deserialization from dictionary"""
        task_data = {
            "id": "test",
            "command": "echo test",
            "status": "pending",
            "priority": 1,
            "tags": ["tag1"],
            "max_retries": 3,
            "retry_count": 0,
            "working_dir": None,
            "env_vars": {},
            "timeout": None,
            "created_at": "2023-01-01T00:00:00",
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        task = Task.from_dict(task_data)
        assert task.id == "test"
        assert task.command == "echo test"
        assert task.priority == 1
        assert task.tags == ["tag1"]


class TestTaskQueue:
    @pytest.fixture
    def temp_queue_file(self):
        """Create a temporary file for task queue"""
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    @pytest.fixture
    def task_queue(self, temp_queue_file):
        """Create a TaskQueue instance"""
        return TaskQueue(temp_queue_file)

    def test_queue_initialization_new_file(self, temp_queue_file):
        """Test initializing queue with new file"""
        queue = TaskQueue(temp_queue_file)
        assert len(queue.tasks) == 0
        assert os.path.exists(temp_queue_file)

    def test_queue_initialization_existing_file(self, temp_queue_file):
        """Test initializing queue with existing file"""
        # Create initial data
        initial_data = {
            "tasks": [{
                "id": "existing",
                "command": "echo existing",
                "status": "pending",
                "priority": 0,
                "tags": [],
                "max_retries": 3,
                "retry_count": 0,
                "working_dir": None,
                "env_vars": {},
                "timeout": None,
                "created_at": "2023-01-01T00:00:00",
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None
            }]
        }
        with open(temp_queue_file, 'w') as f:
            json.dump(initial_data, f)

        queue = TaskQueue(temp_queue_file)
        assert len(queue.tasks) == 1
        assert queue.tasks[0].id == "existing"

    def test_add_task(self, task_queue):
        """Test adding a task to queue"""
        task = Task("test-1", "echo test")
        task_queue.add_task(task)
        
        assert len(task_queue.tasks) == 1
        assert task_queue.tasks[0].id == "test-1"

    def test_priority_ordering(self, task_queue):
        """Test that tasks are ordered by priority"""
        task1 = Task("low", "echo low", priority=1)
        task2 = Task("high", "echo high", priority=10)
        task3 = Task("medium", "echo medium", priority=5)
        
        task_queue.add_task(task1)
        task_queue.add_task(task2)
        task_queue.add_task(task3)
        
        # Should be ordered high to low priority
        assert task_queue.tasks[0].id == "high"
        assert task_queue.tasks[1].id == "medium"
        assert task_queue.tasks[2].id == "low"

    def test_get_next_task_by_priority(self, task_queue):
        """Test getting next task respects priority"""
        task1 = Task("low", "echo low", priority=1)
        task2 = Task("high", "echo high", priority=10)
        
        task_queue.add_task(task1)
        task_queue.add_task(task2)
        
        next_task = task_queue.get_next_task()
        assert next_task.id == "high"

    def test_get_next_task_empty_queue(self, task_queue):
        """Test getting next task from empty queue"""
        next_task = task_queue.get_next_task()
        assert next_task is None

    def test_get_next_task_with_tags(self, task_queue):
        """Test getting next task filtered by tags"""
        task1 = Task("untagged", "echo untagged")
        task2 = Task("tagged", "echo tagged", tags=["batch"])
        task3 = Task("other", "echo other", tags=["interactive"])
        
        task_queue.add_task(task1)
        task_queue.add_task(task2)
        task_queue.add_task(task3)
        
        # Get task with specific tag
        next_task = task_queue.get_next_task(required_tags=["batch"])
        assert next_task.id == "tagged"
        
        # Get task without tag filter
        next_task = task_queue.get_next_task()
        assert next_task.id == "untagged"

    def test_get_task_by_id(self, task_queue):
        """Test retrieving task by ID"""
        task = Task("findme", "echo findme")
        task_queue.add_task(task)
        
        found = task_queue.get_task("findme")
        assert found.id == "findme"
        
        not_found = task_queue.get_task("nonexistent")
        assert not_found is None

    def test_update_task_status(self, task_queue):
        """Test updating task status"""
        task = Task("update-me", "echo test")
        task_queue.add_task(task)
        
        # Update to running
        success = task_queue.update_task_status("update-me", "running")
        assert success is True
        assert task_queue.get_task("update-me").status == "running"
        
        # Try to update non-existent task
        success = task_queue.update_task_status("nonexistent", "running")
        assert success is False

    def test_remove_task(self, task_queue):
        """Test removing task from queue"""
        task = Task("remove-me", "echo test")
        task_queue.add_task(task)
        
        assert len(task_queue.tasks) == 1
        
        success = task_queue.remove_task("remove-me")
        assert success is True
        assert len(task_queue.tasks) == 0
        
        # Try to remove non-existent task
        success = task_queue.remove_task("nonexistent")
        assert success is False

    def test_list_tasks_all(self, task_queue):
        """Test listing all tasks"""
        task1 = Task("task1", "echo 1")
        task2 = Task("task2", "echo 2")
        
        task_queue.add_task(task1)
        task_queue.add_task(task2)
        
        all_tasks = task_queue.list_tasks()
        assert len(all_tasks) == 2

    def test_list_tasks_by_status(self, task_queue):
        """Test listing tasks filtered by status"""
        task1 = Task("pending1", "echo 1")
        task2 = Task("running1", "echo 2")
        task2.status = "running"
        
        task_queue.add_task(task1)
        task_queue.add_task(task2)
        
        pending_tasks = task_queue.list_tasks(status="pending")
        assert len(pending_tasks) == 1
        assert pending_tasks[0].id == "pending1"
        
        running_tasks = task_queue.list_tasks(status="running")
        assert len(running_tasks) == 1
        assert running_tasks[0].id == "running1"

    def test_list_tasks_by_tags(self, task_queue):
        """Test listing tasks filtered by tags"""
        task1 = Task("task1", "echo 1", tags=["batch"])
        task2 = Task("task2", "echo 2", tags=["interactive"])
        task3 = Task("task3", "echo 3", tags=["batch", "important"])
        
        task_queue.add_task(task1)
        task_queue.add_task(task2)
        task_queue.add_task(task3)
        
        batch_tasks = task_queue.list_tasks(tags=["batch"])
        assert len(batch_tasks) == 2
        
        important_tasks = task_queue.list_tasks(tags=["important"])
        assert len(important_tasks) == 1

    def test_save_and_load_persistence(self, temp_queue_file):
        """Test queue persistence across instances"""
        # Create queue and add tasks
        queue1 = TaskQueue(temp_queue_file)
        task = Task("persistent", "echo persistent")
        queue1.add_task(task)
        queue1.save()
        
        # Create new queue instance and verify task exists
        queue2 = TaskQueue(temp_queue_file)
        assert len(queue2.tasks) == 1
        assert queue2.tasks[0].id == "persistent"

    @patch('agentcoord.tasks.FileLock')
    def test_thread_safety_with_lock(self, mock_lock, task_queue):
        """Test that operations use file locking"""
        mock_lock_instance = MagicMock()
        mock_lock.return_value.__enter__ = MagicMock(return_value=mock_lock_instance)
        mock_lock.return_value.__exit__ = MagicMock()
        
        task = Task("test", "echo test")
        task_queue.add_task(task)
        
        # Verify lock was used
        mock_lock.assert_called()