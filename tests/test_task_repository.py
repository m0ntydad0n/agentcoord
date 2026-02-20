import unittest
from task_system.task_repository import TaskRepository


class TestTaskRepository(unittest.TestCase):
    def setUp(self):
        self.repo = TaskRepository()
    
    def test_create_and_get(self):
        task_id = self.repo.create({"action": "test"}, priority=1, tags=["urgent"])
        task = self.repo.get(task_id)
        
        self.assertIsNotNone(task)
        self.assertEqual(task.data["action"], "test")
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.tags, ["urgent"])
        self.assertEqual(task.status, "pending")
    
    def test_update(self):
        task_id = self.repo.create({"action": "test"})
        
        # Update existing task
        self.assertTrue(self.repo.update(task_id, status="processing"))
        task = self.repo.get(task_id)
        self.assertEqual(task.status, "processing")
        
        # Update non-existent task
        self.assertFalse(self.repo.update("fake-id", status="done"))
    
    def test_delete(self):
        task_id = self.repo.create({"action": "test"})
        
        # Delete existing task
        self.assertTrue(self.repo.delete(task_id))
        self.assertIsNone(self.repo.get(task_id))
        
        # Delete non-existent task
        self.assertFalse(self.repo.delete("fake-id"))


if __name__ == '__main__':
    unittest.main()