import tempfile
import unittest
from pathlib import Path

from app.storage import SessionStore
from app.workflow import AgentOrchestrator


class AgentWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SessionStore(Path(self.temp_dir.name) / "sessions.json")
        self.orchestrator = AgentOrchestrator(self.store)

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_support_looks_up_demo_orders_and_checkpoints_turn(self):
        result = await self.orchestrator.run(
            {
                "session_id": "support-test",
                "agent": "support",
                "message": "Where is order DEMO-1001?",
            }
        )

        self.assertIn("shipped", result["reply"])
        self.assertEqual(
            [step["node"] for step in result["workflow"]],
            ["router", "planner", "tool_call", "tool_call", "reflection", "checkpoint"],
        )
        self.assertIn("Turns in this session: 1", result["memory_summary"])

    async def test_support_escalates_sensitive_requests(self):
        result = await self.orchestrator.run(
            {
                "session_id": "escalation-test",
                "agent": "support",
                "message": "I need a human agent to report fraud",
            }
        )

        self.assertTrue(result["escalated"])
        self.assertTrue(result["awaiting_human"])
        self.assertEqual(len(self.store.pending_reviews()["items"]), 1)

    async def test_interview_uses_selected_role_and_difficulty(self):
        result = await self.orchestrator.run(
            {
                "session_id": "interview-test",
                "agent": "interview",
                "message": "start interview",
                "role": "AI Engineer",
                "difficulty": "advanced",
            }
        )

        self.assertIn("AI Engineer", result["reply"])
        self.assertIn("production-ready system", result["reply"])
        self.assertEqual(
            [step["node"] for step in result["workflow"]],
            ["router", "planner", "reflection", "checkpoint"],
        )


if __name__ == "__main__":
    unittest.main()
