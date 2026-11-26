import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class AgentTownEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test-agenttown.db")
        self.db_patch = patch.object(app, "DB_PATH", self.db_path)
        self.db_patch.start()
        app.initialize()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_initializes_five_agents(self):
        state = app.snapshot()
        self.assertEqual(len(state["agents"]), 5)
        self.assertEqual(state["engine"], "local-role-workers")

    def test_creator_decree_executes_and_persists_result(self):
        task_id = app.create_task("Build knowledge archive", "Store shared notes", "developer")
        task = next(t for t in app.snapshot()["tasks"] if t["id"] == task_id)
        self.assertEqual(task["status"], "completed")
        self.assertIn("ENGINEERING WORK PRODUCT", task["result"])
        self.assertIsNotNone(task["completed_at"])

    def test_paused_civilization_queues_work_without_executing(self):
        app.set_paused(True)
        task_id = app.create_task("Wait for resume", "", "mayor")
        task = next(t for t in app.snapshot()["tasks"] if t["id"] == task_id)
        self.assertEqual(task["status"], "queued")
        self.assertFalse(app.execute(task_id))
        app.set_paused(False)
        self.assertTrue(app.execute(task_id))

    def test_council_runs_all_five_workers(self):
        task_ids = app.council()
        self.assertEqual(len(task_ids), 5)
        state = app.snapshot()
        self.assertEqual(state["counts"].get("completed"), 5)
        self.assertEqual(state["counts"].get("queued", 0), 0)

    def test_rejects_empty_goal_and_unknown_agent(self):
        with self.assertRaises(ValueError):
            app.create_task("   ", "", "mayor")
        with self.assertRaises(ValueError):
            app.create_task("Valid goal", "", "unknown")

    def test_completed_task_cannot_execute_twice(self):
        task_id = app.create_task("One-time task", "", "auditor")
        self.assertFalse(app.execute(task_id))
        state = app.snapshot()
        self.assertEqual(state["counts"].get("completed"), 1)


if __name__ == "__main__":
    unittest.main()
