from typing import Annotated, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been met")
    user_input_needed: bool = Field(
        description="True if more input is needed from the user, or clarifications, or the assistant is stuck"
    )


class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

    # INPUT
    success_criteria: str

    # PLANNING
    plan: Optional[str]

    # EVALUATION
    feedback_on_work: Optional[str]
    success_criteria_met: bool

    # CONTROL
    user_input_needed: bool
