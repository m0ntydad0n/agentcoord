import unittest
from task_system.task_repository import TaskRepository
from task_system.task_claimer import TaskClaimer


class TestTaskClaimer(unittest.TestCase):
    def setUp(self):
        self.repo = TaskRepository()
        self.claimer = TaskClaimer(self.repo)
    
    def test_claim_task(self):
        task_id = self.repo.create({"action": "test"})
        
        # Successful claim
        self.assertTrue(self.claimer.claim_task(task_id, "worker-1"))
        task = self.repo.get(task_id)
        self.assertEqual(task.claimed_by, "worker-1")
        self.assertEqual(task.status, "claimed")
        
        # Cannot claim already claimed task
        self.assertFalse(self.claimer.claim_task(task_id, "worker-2"))
    
    def test_release_task(self):
        task_id = self.repo.create({"action": "test"})
        self.claimer.claim_task(task_id, "worker-1")
        
        # Release with correct claimer
        self.assertTrue(self.claimer.release_task(task_id, "worker-1"))
        task = self.repo.get(task_id)
        self.assertIsNone(task.claimed_by)
        self.assertEqual(task.status, "pending")
    
    def test_complete_task(self):
        task_id = self.repo.create({"action": "test"})
        self.claimer.claim_task(task_id, "worker-1")
        
        # Complete with correct claimer
        self.assertTrue(self.claimer.complete_task(task_id, "worker-1"))
        task = self.repo.get(task_id)
        self.assertEqual(task.status, "completed")


if __name__ == '__main__':
    unittest.main()