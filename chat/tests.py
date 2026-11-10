import os
from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import TestCase, SimpleTestCase
from . import tools
from .agent import get_client, run_agent


class InventoryTests(TestCase):
    def test_inventory_lifecycle(self):
        self.assertTrue(tools.add_item("Hammer", 20)["created"])
        self.assertEqual(tools.add_item("hammer", 5)["quantity"], 25)
        self.assertEqual(tools.check_stock("HAMMER")["quantity"], 25)
        self.assertIn("error", tools.remove_stock("Hammer", 26))
        self.assertEqual(tools.remove_stock("Hammer", 3)["quantity"], 22)
        self.assertEqual(tools.list_items()["items"], [{"name": "Hammer", "quantity": 22}])
        tools.delete_item("Hammer")
        self.assertIn("error", tools.check_stock("Hammer"))

    def test_missing_item(self):
        self.assertIn("error", tools.remove_stock("missing", 1))
        self.assertIn("error", tools.delete_item("missing"))


class WebTests(TestCase):
    def test_home_and_health_without_api_key(self):
        self.assertContains(self.client.get("/"), "Inventory Agent")
        self.assertEqual(self.client.get("/health/").json(), {"status": "ok"})

    @patch("chat.views.run_agent", return_value=("Added 15 hammers.", "interaction-1"))
    def test_chat_keeps_session(self, agent):
        self.client.post("/", {"message": "Add 15 hammers"})
        self.client.post("/", {"message": "How many now?"})
        agent.assert_called_with("How many now?", "interaction-1")
        self.assertEqual(len(self.client.session["history"]), 4)
        self.assertContains(self.client.get("/"), "Added 15 hammers.")

    @patch("chat.views.run_agent")
    def test_blank_message(self, agent):
        self.client.post("/", {"message": "   "})
        agent.assert_not_called()

    @patch("chat.views.run_agent", side_effect=RuntimeError("private-key-value"))
    def test_error_does_not_expose_secrets(self, agent):
        with self.assertLogs("chat.views", level="ERROR"):
            self.client.post("/", {"message": "hello"})
        response = self.client.get("/")
        self.assertNotContains(response, "private-key-value")
        self.assertContains(response, "The agent is unavailable")

    def test_reset(self):
        session = self.client.session
        session["history"] = [{"role": "user", "text": "test"}]
        session.save()
        self.client.get("/reset/")
        self.assertNotIn("history", self.client.session)


class AgentTests(SimpleTestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_key_is_only_needed_when_chat_runs(self):
        with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
            get_client()

    @patch("chat.agent.get_client")
    def test_tool_call_then_answer(self, get_client_mock):
        client = get_client_mock.return_value
        client.interactions.create.side_effect = [
            SimpleNamespace(id="call-1", steps=[SimpleNamespace(type="function_call", name="list_items", arguments={}, id="tool-1")]),
            SimpleNamespace(id="answer-1", steps=[], output_text="No items."),
        ]
        with patch.dict("chat.agent.TOOL_FUNCTIONS", {"list_items": Mock(return_value={"items": []})}):
            self.assertEqual(run_agent("List stock"), ("No items.", "answer-1"))
        sent = client.interactions.create.call_args.kwargs
        self.assertEqual(sent["previous_interaction_id"], "call-1")
        self.assertEqual(sent["input"][0]["call_id"], "tool-1")

    @patch("chat.agent.get_client")
    def test_agent_loop_is_bounded(self, get_client_mock):
        client = get_client_mock.return_value
        client.interactions.create.return_value = SimpleNamespace(id="loop", steps=[SimpleNamespace(type="function_call", name="list_items", arguments={}, id="tool")])
        with patch.dict("chat.agent.TOOL_FUNCTIONS", {"list_items": Mock(return_value={"items": []})}):
            answer, _ = run_agent("List stock")
        self.assertIn("try rephrasing", answer)
        self.assertEqual(client.interactions.create.call_count, 6)
