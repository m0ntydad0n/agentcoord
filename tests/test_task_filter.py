import unittest
from task_system.task_repository import TaskRepository
from task_system.task_filter import TaskFilter


class TestTaskFilter(unittest.TestCase):
    def setUp(self):
        self.repo = TaskRepository()
        self.filter = TaskFilter(self.repo)
        
        # Create test tasks
        self.task1 = self.repo.create({"action": "test1"}, priority=1, tags=["urgent", "api"])
        self.task2 = self.repo.create({"action": "test2"}, priority=5, tags=["normal"])
        self.task3 = self.repo.create({"action": "test3"}, priority=3, tags=["urgent"])
        
        # Set one task to completed
        self.repo.update(self.task2, status="completed")
    
    def test_get_by_status(self):
        pending = self.filter.get_by_status("pending")
        completed = self.filter.get_by_status("completed")
        
        self.assertEqual(len(pending), 2)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].id, self.task2)
    
    def test_get_by_tags(self):
        # Match any
        urgent_tasks = self.filter.get_by_tags(["urgent"])
        self.assertEqual(len(urgent_tasks), 2)
        
        # Match all