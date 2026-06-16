"""
End-to-end agent evaluation.

Runs each test scenario through the full production graph (planner → worker →
evaluator loop) and scores the final reply with an LLM judge across five
dimensions: resolution, accuracy, tone, completeness, and scope adherence.
"""

import uuid
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from src.config import LLM_MODEL
from src.agent.graph import build_graph
from src.retriever import build_retrieval_tool


# Test cases

E2E_TEST_CASES: List[Dict[str, str]] = [
    {
        "scenario": "Refund request",
        "message": (
            "I bought a product 5 days ago and it stopped working. "
            "I want a full refund. What is your refund policy and how do I start the process?"
        ),
        "success_criteria": (
            "Explain the refund policy clearly including the eligibility window and the steps "
            "to initiate a refund. Tone must be empathetic."
        ),
    },
    {
        "scenario": "Shipping inquiry",
        "message": (
            "I placed an order yesterday. How long will standard shipping take "
            "and is expedited shipping available?"
        ),
        "success_criteria": (
            "Provide accurate shipping timeframes and available options based on the knowledge base."
        ),
    },
    {
        "scenario": "Account recovery",
        "message": (
            "I can't log into my account. I think I forgot my password "
            "and my recovery email may have changed too."
        ),
        "success_criteria": (
            "Walk the customer through account recovery steps clearly and empathetically. "
            "Offer escalation if self-service steps are insufficient."
        ),
    },
    {
        "scenario": "Order tracking delay",
        "message": (
            "My order was supposed to arrive 3 days ago but it still hasn't. "
            "The tracking page just says 'in transit'."
        ),
        "success_criteria": (
            "Provide clear guidance on what to do when an order is delayed, "
            "including escalation options if the issue cannot be resolved."
        ),
    },
    {
        "scenario": "Payment failure",
        "message": (
            "I keep getting a payment declined error at checkout. "
            "I have tried two different credit cards and the same thing happens."
        ),
        "success_criteria": (
            "Provide actionable troubleshooting steps for payment failures "
            "and offer escalation to a human agent if the steps don't resolve it."
        ),
    },
    {
        "scenario": "Warranty claim",
        "message": (
            "My Smartwatch X screen stopped working after 8 months. "
            "I haven't dropped it or damaged it. Am I covered under warranty "
            "and what do I need to do to file a claim?"
        ),
        "success_criteria": (
            "Confirm warranty coverage for a manufacturing defect within the coverage period, "
            "explain the claim process including any required documentation, "
            "and set clear expectations on timeline and outcome."
        ),
    },
    {
        "scenario": "Product troubleshooting — earbuds",
        "message": (
            "One of my Wireless Earbuds Pro stopped making any sound at all. "
            "The other earbud works fine. I tried re-pairing but nothing changed."
        ),
        "success_criteria": (
            "Provide step-by-step troubleshooting for a single non-functioning earbud "
            "(including reset steps), and offer warranty or escalation if troubleshooting fails."
        ),
    },
    {
        "scenario": "Billing dispute — duplicate charge",
        "message": (
            "I see two identical charges on my credit card from your store for the same order. "
            "I only placed the order once. Can you help me get the duplicate charge reversed?"
        ),
        "success_criteria": (
            "Acknowledge the concern empathetically, explain how to verify whether the second "
            "charge is a hold or a true duplicate, describe the refund process with a clear "
            "timeline, and offer escalation to the billing team if needed."
        ),
    },
    {
        "scenario": "Out-of-scope boundary test",
        "message": (
            "Can you write me a Python script to scrape product prices "
            "from competitor websites?"
        ),
        "success_criteria": (
            "Politely decline the out-of-scope request and redirect the user "
            "to legitimate customer support topics only. Do not assist with the task."
        ),
    },
]


# Judge scoring model

class E2EScores(BaseModel):
    resolution: float     = Field(description="0.0–1.0: Was the issue addressed or resolved?")
    accuracy: float       = Field(description="0.0–1.0: Is the information factually correct?")
    tone: float           = Field(description="0.0–1.0: Was the tone empathetic and professional?")
    completeness: float   = Field(description="0.0–1.0: Were all parts of the question answered?")
    scope_adherence: float = Field(description="0.0–1.0: Did the agent stay within its support scope?")
    reasoning: str        = Field(description="Brief explanation of the scores (2-3 sentences)")


 
# Main evaluation runner


async def run_e2e_evaluation(retriever) -> Dict[str, Any]:
    
    print("END-TO-END AGENT EVALUATION")
    
    retrieval_tool = build_retrieval_tool(retriever)
    graph = build_graph(all_tools=[retrieval_tool], checkpointer=MemorySaver())

    judge_llm = ChatOpenAI(model=LLM_MODEL, temperature=0).with_structured_output(E2EScores)

    async def judge(tc: Dict[str, str], reply: str) -> E2EScores:
        prompt = (
            f"Customer message: {tc['message']}\n\n"
            f"Success criteria: {tc['success_criteria']}\n\n"
            f"Agent reply:\n{reply}\n\n"
            "Score each dimension 0.0–1.0."
        )
        return await judge_llm.ainvoke([HumanMessage(content=prompt)])

    results = []
    for tc in E2E_TEST_CASES:
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        state = {
            "messages": [{"role": "user", "content": tc["message"]}],
            "success_criteria": tc["success_criteria"],
            "plan": None,
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }
        result = await graph.ainvoke(state, config=config)

        # The last message is the evaluator's internal feedback; [-2] is the worker's reply.
        reply = result["messages"][-2].content
        scores = await judge(tc, reply)
        avg = (
            scores.resolution
            + scores.accuracy
            + scores.tone
            + scores.completeness
            + scores.scope_adherence
        ) / 5

        print(f"\nScenario: {tc['scenario']}")
        print(
            f"  R:{scores.resolution:.1f}  A:{scores.accuracy:.1f}  "
            f"T:{scores.tone:.1f}  C:{scores.completeness:.1f}  "
            f"S:{scores.scope_adherence:.1f}  →  Avg:{avg:.2f}"
        )
        print(f"  {scores.reasoning}")
        results.append({"scenario": tc["scenario"], "avg": avg, "scores": scores})

    dims = ["resolution", "accuracy", "tone", "completeness", "scope_adherence"]
    summary = {d: sum(getattr(r["scores"], d) for r in results) / len(results) for d in dims}
    summary["overall"] = sum(summary[d] for d in dims) / len(dims)

    print("E2E SUMMARY")
    for k, v in summary.items():
        bar = "█" * int(v * 10) + "░" * (10 - int(v * 10))
        print(f"  {k:<18} {bar}  {v:.2f}")
    return {
        "results": [{"scenario": r["scenario"], "avg": r["avg"]} for r in results],
        "summary": summary,
    }
