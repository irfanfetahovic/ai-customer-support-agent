from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agent.nodes import format_conversation, route_based_on_evaluation, worker_router


class TestWorkerRouter:
    def _make_state(self, message):
        return {"messages": [message]}

    def test_routes_to_tools_when_tool_calls_present(self):
        # spec restricts the mock to only have attributes/methods of AIMessage, which includes tool_calls
        message = MagicMock(spec=AIMessage)
        message.tool_calls = [{"name": "lookup_order_status", "args": {}, "id": "1"}]
        assert worker_router(self._make_state(message)) == "tools"

    def test_routes_to_evaluator_when_no_tool_calls(self):
        message = MagicMock(spec=AIMessage)
        message.tool_calls = []
        assert worker_router(self._make_state(message)) == "evaluator"

    def test_routes_to_evaluator_when_tool_calls_attribute_missing(self):
        message = MagicMock(spec=[])  # no tool_calls attribute
        assert worker_router(self._make_state(message)) == "evaluator"

    def test_uses_last_message_only(self):
        earlier = MagicMock(spec=AIMessage)
        earlier.tool_calls = [{"name": "some_tool", "args": {}, "id": "1"}]
        last = MagicMock(spec=AIMessage)
        last.tool_calls = []
        state = {"messages": [earlier, last]}
        assert worker_router(state) == "evaluator"


class TestRouteBasedOnEvaluation:
    def test_ends_when_success_criteria_met(self):
        state = {"success_criteria_met": True, "user_input_needed": False}
        assert route_based_on_evaluation(state) == "END"

    def test_ends_when_user_input_needed(self):
        state = {"success_criteria_met": False, "user_input_needed": True}
        assert route_based_on_evaluation(state) == "END"

    def test_ends_when_both_true(self):
        state = {"success_criteria_met": True, "user_input_needed": True}
        assert route_based_on_evaluation(state) == "END"

    def test_routes_to_worker_when_criteria_not_met_and_no_input_needed(self):
        state = {"success_criteria_met": False, "user_input_needed": False}
        assert route_based_on_evaluation(state) == "worker"


class TestFormatConversation:
    def test_human_message_labeled_as_user(self):
        result = format_conversation([HumanMessage(content="Where is my order?")])
        assert "User: Where is my order?" in result

    def test_ai_message_labeled_as_assistant(self):
        result = format_conversation([AIMessage(content="Your order is on the way.")])
        assert "Assistant: Your order is on the way." in result

    def test_ai_message_with_no_content_shows_placeholder(self):
        msg = AIMessage(content="")
        result = format_conversation([msg])
        assert "Assistant: [Tools use]" in result

    def test_multiple_messages_preserved_in_order(self):
        messages = [
            HumanMessage(content="Hi"),
            AIMessage(content="Hello, how can I help?"),
            HumanMessage(content="My order is late."),
        ]
        result = format_conversation(messages)
        assert result.index("User: Hi") < result.index("Assistant: Hello") < result.index("User: My order is late.")

    def test_output_starts_with_header(self):
        result = format_conversation([])
        assert result.startswith("Conversation history:")

    def test_non_human_non_ai_messages_are_ignored(self):
        result = format_conversation([SystemMessage(content="You are a support agent.")])
        assert "You are a support agent." not in result
