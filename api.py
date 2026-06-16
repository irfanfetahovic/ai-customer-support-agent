"""
FastAPI Application — AI Customer Support Agent

Run locally:
    uv run uvicorn api:app --reload

The /docs endpoint provides auto-generated OpenAPI documentation.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.config import DEFAULT_SUCCESS_CRITERIA
from src.guardrails import check_input_guardrails, check_moderation, make_thread_id
from src.retriever import build_customer_support_retriever, build_retrieval_tool
from src.mcp_client import connect_mcp_server
from src.agent.graph import build_graph, create_checkpointer



# Global state — initialised once on startup

_graph = None
_mcp_client = None  # kept alive to hold the MCP subprocess connection open
_conn = None        # kept alive to hold the aiosqlite connection open
_init_lock = asyncio.Lock()


async def _ensure_initialized() -> None:
    """Initialise the retriever, MCP client, and LangGraph graph on first use."""
    global _graph, _mcp_client, _conn

    if _graph is not None:
        return

    async with _init_lock:
        if _graph is not None:  # double-checked locking
            return

        retriever, _, _ = build_customer_support_retriever()
        retrieval_tool = build_retrieval_tool(retriever)

        _mcp_client, mcp_tools = await connect_mcp_server()

        all_tools = [retrieval_tool] + mcp_tools

        checkpointer, _conn = await create_checkpointer()

        _graph = build_graph(all_tools, checkpointer)
        print("Agent graph initialised successfully.")


# Lifespan — warm up the agent on startup so the first /chat call is fast
@asynccontextmanager 
async def lifespan(app: FastAPI):
# lifespan function is called when the FastAPI app starts up and shuts down, allowing us to perform any necessary setup or cleanup tasks
# lifespan is async generator function that yields control to the FastAPI app and then performs cleanup on shutdown
    await _ensure_initialized() # startup: warm up the agent graph
    yield # app lifespan context manager yields control to the FastAPI app
    # Cleanup: close the aiosqlite connection when the server shuts down
    if _conn is not None:
        await _conn.close()


# FastAPI app

app = FastAPI(
    title="AI Customer Support Agent",
    description=(
        "A multi-agent LangGraph pipeline for customer support. "
        "Planner → Worker (RAG + custom tools) → Evaluator with quality-based re-routing."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# Pydantic models
# They are used for request validation and response serialization in the FastAPI endpoints.

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        description="The customer's support message.",
        examples=["Where is my order ORD-1002?"],
    )
    thread_id: str = Field(
        default_factory=make_thread_id, # generate a new thread ID if not provided,
        description=(
            "Conversation thread identifier for multi-turn sessions. "
            "Omit to start a new conversation; reuse to continue an existing one."
        ),
    )
    success_criteria: str = Field(
        default=DEFAULT_SUCCESS_CRITERIA,
        description="Criteria the evaluator agent uses to judge response quality.",
    )


class ChatResponse(BaseModel):
    reply: str = Field(description="The support agent's response to the customer.")
    evaluator_feedback: str = Field(
        description="Internal quality assessment from the evaluator agent."
    )
    thread_id: str = Field(
        description="Thread ID to pass on subsequent requests to continue this conversation."
    )
    guardrail_triggered: bool = Field(
        default=False,
        description="True if a guardrail blocked the message before reaching the agent.",
    )


class ResetResponse(BaseModel):
    thread_id: str = Field(
        description="A fresh thread ID. Pass this as thread_id in future /chat requests."
    )


class HealthResponse(BaseModel):
    status: str = Field(description="Service liveness status.", examples=["ok"])
    agent_ready: bool = Field(description="True once the agent graph has been initialised.")


# Endpoints

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    tags=["Operations"],
)
async def health() -> HealthResponse:
    """Returns the service liveness status and whether the agent is ready."""
    return HealthResponse(status="ok", agent_ready=_graph is not None)


@app.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the support agent",
    tags=["Chat"],
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a customer support message and receive an agent reply.

    - Applies input guardrails (injection detection, length limits, OpenAI Moderation).
    - Runs the Planner → Worker → Evaluator LangGraph pipeline.
    - Applies output moderation before returning the reply.
    - Use the same `thread_id` across requests to hold a multi-turn conversation.
    """
    await _ensure_initialized()

    # Tier 1: rule-based guardrails (fast, zero token cost)
    rule_error = check_input_guardrails(request.message)
    if rule_error:
        return ChatResponse(
            reply=f"[Guardrail] {rule_error}",
            evaluator_feedback="",
            thread_id=request.thread_id,
            guardrail_triggered=True,
        )

    # Tier 3: OpenAI Moderation API
    moderation_error = await check_moderation(request.message)
    if moderation_error:
        return ChatResponse(
            reply=f"[Guardrail] {moderation_error}",
            evaluator_feedback="",
            thread_id=request.thread_id,
            guardrail_triggered=True,
        )

    config = {"configurable": {"thread_id": request.thread_id}}
    state = {
        "messages": [{"role": "user", "content": request.message}],
        "success_criteria": request.success_criteria,
        "feedback_on_work": None,
        "success_criteria_met": False,
        "user_input_needed": False,
    }

    try:
        result = await _graph.ainvoke(state, config=config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    # Second-to-last message is the worker reply; last is the evaluator feedback.
    reply_content: str = result["messages"][-2].content
    evaluator_content: str = result["messages"][-1].content

    # Output moderation
    output_moderation_error = await check_moderation(reply_content)
    if output_moderation_error:
        reply_content = (
            "[Guardrail] The agent's response was blocked for safety reasons. "
            "Please contact our support team directly for assistance."
        )

    return ChatResponse(
        reply=reply_content,
        evaluator_feedback=evaluator_content,
        thread_id=request.thread_id,
        guardrail_triggered=False,
    )


@app.post(
    "/chat/reset",
    response_model=ResetResponse,
    summary="Start a new conversation thread",
    tags=["Chat"],
)
async def chat_reset() -> ResetResponse:
    """
    Generate a fresh `thread_id` to start a new conversation.

    The previous thread's history is preserved in the database but will no
    longer be referenced by new requests using the returned thread ID.
    """
    return ResetResponse(thread_id=make_thread_id())
