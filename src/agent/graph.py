import aiosqlite
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode

from src.config import DB_PATH
from src.agent.state import State
from src.agent.nodes import AgentNodes, worker_router, route_based_on_evaluation


async def create_checkpointer():
    """Create an async SQLite checkpointer for persistent conversation memory.

    The caller must keep a reference to the returned connection to keep it open
    for the lifetime of the session.

    Returns (checkpointer, connection).
    """
    conn = await aiosqlite.connect(DB_PATH)
    return AsyncSqliteSaver(conn), conn


def build_graph(all_tools: list, checkpointer):
    """Build and compile the LangGraph agent graph.

    Args:
        all_tools:    Full toolset (retrieval tool + MCP tools) bound to the worker.
        checkpointer: LangGraph checkpointer — AsyncSqliteSaver for production,
                      MemorySaver for testing/evaluation.

    Returns the compiled graph.
    """
    nodes = AgentNodes(all_tools)

    graph_builder = StateGraph(State)

    # Nodes
    graph_builder.add_node("planner", nodes.planner)
    graph_builder.add_node("worker", nodes.worker)
    graph_builder.add_node("tools", ToolNode(all_tools))
    graph_builder.add_node("evaluator", nodes.evaluator)

    # Edges
    graph_builder.add_edge(START, "planner")
    graph_builder.add_edge("planner", "worker")
    graph_builder.add_conditional_edges(
        "worker", worker_router, {"tools": "tools", "evaluator": "evaluator"}
    )
    graph_builder.add_edge("tools", "worker")
    graph_builder.add_conditional_edges(
        "evaluator", route_based_on_evaluation, {"END": END, "worker": "worker"}
    )

    return graph_builder.compile(checkpointer=checkpointer)
