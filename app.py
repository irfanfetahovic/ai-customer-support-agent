"""
Gradio Demo App — AI Customer Support Agent

Run locally:
    uv run python app.py

Hugging Face Spaces:
    This file is the Space entry point. Set `app_file: app.py` in the
    Space README.md YAML frontmatter.
"""

import asyncio

import gradio as gr

from src.config import DEFAULT_SUCCESS_CRITERIA
from src.guardrails import check_input_guardrails, check_moderation, make_thread_id
from src.retriever import build_customer_support_retriever, build_retrieval_tool
from src.mcp_client import connect_mcp_server
from src.agent.graph import build_graph, create_checkpointer


# Lazy global initialization — runs once on first message, inside Gradio's
# event loop. This avoids event-loop conflicts between asyncio.run() and the
# loop that Gradio/anyio manages internally.

_graph = None
_mcp_client = None  # kept alive to hold the MCP subprocess connection open
_conn = None        # kept alive to hold the aiosqlite connection open
_init_lock = asyncio.Lock() # to prevent race conditions on first initialization between multiple users


async def _ensure_initialized() -> None:
    """Initialize the retriever, MCP client, and LangGraph graph on first use."""
    global _graph, _mcp_client, _conn

    if _graph is not None:
        return

    async with _init_lock:
        if _graph is not None:  # double-checked locking
            return

        # RAG: build the hybrid retriever and wrap it as a LangChain Tool
        retriever, _, _ = build_customer_support_retriever()
        retrieval_tool = build_retrieval_tool(retriever)

        # MCP: connect to the CRM server subprocess and collect allowed tools
        _mcp_client, mcp_tools = await connect_mcp_server()

        all_tools = [retrieval_tool] + mcp_tools

        # Persistent memory: async SQLite checkpointer
        checkpointer, _conn = await create_checkpointer()

        _graph = build_graph(all_tools, checkpointer)
        print("Agent graph initialised successfully.")



# Event handlers

async def process_message(
    message: str,
    success_criteria: str,
    history: list,
    thread: str,
):
    """Send a user message through the agent pipeline and return the updated history."""
    await _ensure_initialized()

    # Tier 1: rule-based guardrails (fast, zero token cost)
    error = check_input_guardrails(message)
    if error:
        return history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": f"[Guardrail] {error}"},
        ]

    # Tier 3: OpenAI Moderation API (catches harmful content missed by regex)
    moderation_error = await check_moderation(message)
    if moderation_error:
        return history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": f"[Guardrail] {moderation_error}"},
        ]

    config = {"configurable": {"thread_id": thread}}
    state = {
        "messages": [{"role": "user", "content": message}],
        "success_criteria": success_criteria or DEFAULT_SUCCESS_CRITERIA,
        "feedback_on_work": None,
        "success_criteria_met": False,
        "user_input_needed": False,
    }

    result = await _graph.ainvoke(state, config=config)

    # The worker reply is the second-to-last message; the last is the evaluator feedback.
    reply_content = result["messages"][-2].content

    # Tier 3 output moderation: safety-check the agent's reply before returning it.
    output_moderation_error = await check_moderation(reply_content)
    if output_moderation_error:
        reply = {
            "role": "assistant",
            "content": (
                "[Guardrail] The agent's response was blocked for safety reasons. "
                "Please contact our support team directly for assistance."
            ),
        }
    else:
        reply = {"role": "assistant", "content": reply_content}

    feedback = {"role": "assistant", "content": result["messages"][-1].content}
    return history + [{"role": "user", "content": message}, reply, feedback]


async def reset():
    """Clear the conversation and start a fresh thread."""
    return "", DEFAULT_SUCCESS_CRITERIA, [], make_thread_id()


# Gradio UI

_theme = gr.themes.Default(primary_hue="emerald")

with gr.Blocks(theme=_theme) as demo:
    gr.Markdown(
        """
        # AI Customer Support Agent

        An autonomous multi-agent system that handles customer support for a consumer electronics store.
        Ask about orders, refunds, shipping, warranties, product troubleshooting, or account issues.

        **How it works:** A *planner* agent breaks down your issue → a *worker* agent retrieves knowledge
        and calls CRM tools → an *evaluator* agent scores the response and re-routes if quality falls short.

        **Try asking things like:**
        - *"Where is my order ORD-1002?"*
        - *"I want to return my wireless earbuds — what's the process?"*
        - *"My Smartwatch X won't turn on after charging."*
        - *"Can I get a refund if it's been 25 days since purchase?"*

        The **evaluator feedback** shown after each reply is the quality-assurance agent's internal
        assessment — it's exposed here so you can see the self-evaluation loop in action.

        The **success criteria** field controls what the evaluator checks for. Edit it to test the agent
        against custom scenarios, or leave it as the default.
        """
    )

    # gr.State with a callable generates a fresh value per browser session.
    thread = gr.State(make_thread_id)

    with gr.Row():
        chatbot = gr.Chatbot(label="Support Agent", height=450)

    with gr.Group():
        with gr.Row():
            message = gr.Textbox(
                show_label=False,
                placeholder="Describe your issue or question...",
                lines=1,
            )
        with gr.Row():
            success_criteria = gr.Textbox(
                show_label=False,
                placeholder="Success criteria (leave blank to use default)",
                value=DEFAULT_SUCCESS_CRITERIA,
                lines=2,
            )

    with gr.Row():
        reset_button = gr.Button("Reset", variant="stop")
        go_button = gr.Button("Send", variant="primary")

    # Enter in either text box also submits.
    message.submit(
        process_message,
        inputs=[message, success_criteria, chatbot, thread],
        outputs=[chatbot],
    )
    go_button.click(
        process_message,
        inputs=[message, success_criteria, chatbot, thread],
        outputs=[chatbot],
    )
    reset_button.click(
        reset,
        inputs=[],
        outputs=[message, success_criteria, chatbot, thread],
    )


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Default(primary_hue="emerald"))
