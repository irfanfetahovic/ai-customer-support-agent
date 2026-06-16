import pytest
from pydantic import ValidationError
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.agent.state import EvaluatorOutput, State


class TestEvaluatorOutput:
    def test_valid_instantiation(self):
        obj = EvaluatorOutput(
            feedback="Looks good.",
            success_criteria_met=True,
            user_input_needed=False,
        )
        assert obj.feedback == "Looks good."
        assert obj.success_criteria_met is True
        assert obj.user_input_needed is False

    def test_missing_feedback_raises(self):
        with pytest.raises(ValidationError):
            EvaluatorOutput(success_criteria_met=True, user_input_needed=False)

    def test_missing_success_criteria_met_raises(self):
        with pytest.raises(ValidationError):
            EvaluatorOutput(feedback="ok", user_input_needed=False)

    def test_missing_user_input_needed_raises(self):
        with pytest.raises(ValidationError):
            EvaluatorOutput(feedback="ok", success_criteria_met=True)


class TestState:
    def test_minimal_valid_state(self):
        state: State = {
            "messages": [],
            "success_criteria": "Resolve the issue.",
            "plan": None,
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }
        assert state["success_criteria"] == "Resolve the issue."
        assert state["messages"] == []
        assert state["plan"] is None
        assert state["feedback_on_work"] is None
        assert state["success_criteria_met"] is False
        assert state["user_input_needed"] is False

    def test_state_with_messages(self):
        msgs = [HumanMessage(content="Hello"), AIMessage(content="Hi there")]
        state: State = {
            "messages": msgs,
            "success_criteria": "Answer the user.",
            "plan": None,
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }
        assert len(state["messages"]) == 2
        assert isinstance(state["messages"][0], HumanMessage)
        assert isinstance(state["messages"][1], AIMessage)

    def test_state_messages_accepts_various_message_types(self):
        msgs = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="I need help."),
            AIMessage(content="Sure, how can I help?"),
        ]
        state: State = {
            "messages": msgs,
            "success_criteria": "Help the user.",
            "plan": None,
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }
        assert len(state["messages"]) == 3
        assert isinstance(state["messages"][0], SystemMessage)
