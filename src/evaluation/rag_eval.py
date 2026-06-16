"""
RAG evaluation — 4 layers:
  L1  Source hit rate + per-chunk relevance
  L2  Context quality  (sufficiency, redundancy)
  L3  Generation quality (answer relevance, completeness)
  L4  Faithfulness  (fraction of claims grounded in context)
Note: This module uses a custom LLM-as-judge approach rather than the RAGAS framework used in the notebook.
RAGAS is better for reproducibility, but the custom approach here adds two extra dimensions (context
sufficiency and redundancy). 
"""

import asyncio
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import LLM_MODEL


# Test cases

RAG_TEST_CASES: List[Dict[str, Any]] = [
    # --- Refund ---
    {
        "query": "What is your refund policy? How many days do I have to request a refund?",
        "expected_sources": ["refund_policy", "refunds"],
    },
    # --- Shipping ---
    {
        "query": "How long does standard shipping take and what are the delivery costs?",
        "expected_sources": ["shipping"],
    },
    # --- Account ---
    {
        "query": "How do I recover my account if I forgot my password?",
        "expected_sources": ["account_recovery"],
    },
    # --- Privacy ---
    {
        "query": "What personal data do you collect and how is my privacy protected?",
        "expected_sources": ["privacy"],
    },
    # --- Order tracking ---
    {
        "query": "My order is late and the tracking page is not updating. What should I do?",
        "expected_sources": ["order_tracking"],
    },
    # --- Payment ---
    {
        "query": "My credit card payment was declined at checkout. How do I fix this?",
        "expected_sources": ["payment_issues"],
    },
    # --- Returns ---
    {
        "query": "What is the process to return a defective product?",
        "expected_sources": ["returns", "refund_policy"],
    },
    # --- Warranty — split: coverage eligibility vs. claim process ---
    {
        "query": "Is my product covered under warranty for manufacturing defects?",
        "expected_sources": ["warranty_policy", "warranty"],
    },
    {
        "query": "How do I submit a warranty claim?",
        "expected_sources": ["warranty_policy", "warranty"],
    },
    # --- Billing ---
    {
        "query": "I was charged twice for the same order. How do I dispute a duplicate charge?",
        "expected_sources": ["billing_dispute"],
    },
    # --- Smartwatch troubleshooting ---
    {
        "query": "My Smartwatch X screen went blank and won't turn on after charging. How do I fix it?",
        "expected_sources": ["smartwatch_x_troubleshooting"],
    },
    # --- Earbuds troubleshooting ---
    {
        "query": "Only one of my Wireless Earbuds Pro is connecting to my phone. What should I do?",
        "expected_sources": ["wireless_earbuds_troubleshooting"],
    },
    # --- Order modification ---
    {
        "query": "Can I modify or cancel my order after placing it? How long do I have to make changes?",
        "expected_sources": ["general_faq"],
    },
    # --- Escalation ---
    {
        "query": "My issue has not been resolved after two attempts. How do I escalate to a human agent or manager?",
        "expected_sources": ["escalation"],
    },
    # --- International shipping — split: destinations / costs / duties ---
    {
        "query": "Do you ship internationally, including to Canada and the UK?",
        "expected_sources": ["shipping_policy"],
    },
    {
        "query": "What are the international shipping costs?",
        "expected_sources": ["shipping_policy"],
    },
    {
        "query": "Who pays customs duties on international orders?",
        "expected_sources": ["shipping_policy"],
    },
    # --- Smartwatch X product info — split: features / battery / iPhone compatibility ---
    {
        "query": "What are the key features of the Smartwatch X?",
        "expected_sources": ["smartwatch_x"],
    },
    {
        "query": "What is the battery life of the Smartwatch X?",
        "expected_sources": ["smartwatch_x"],
    },
    {
        "query": "Is the Smartwatch X compatible with iPhone?",
        "expected_sources": ["smartwatch_x"],
    },
    # --- Wireless Earbuds Pro product info — split: battery / ANC ---
    {
        "query": "What is the battery life of the Wireless Earbuds Pro?",
        "expected_sources": ["wireless_earbuds"],
    },
    {
        "query": "Does the Wireless Earbuds Pro support active noise cancellation?",
        "expected_sources": ["wireless_earbuds"],
    },
]


# Pydantic scoring models

class ContextQualityScore(BaseModel):
    sufficiency: float = Field(description="0–1: context contains enough info to answer")
    redundancy: float = Field(description="0–1: how repetitive are the chunks")
    reasoning: str


class GenerationQualityScore(BaseModel):
    answer: str
    relevance: float = Field(description="0–1: answer directly addresses query")
    completeness: float = Field(description="0–1: all parts of query answered")


class FaithfulnessScore(BaseModel):
    score: float = Field(description="0–1: fraction of claims supported by context")
    unsupported_claims: List[str]
    reasoning: str


# Core scoring helpers

async def score_chunk_relevance(llm: ChatOpenAI, query: str, chunk: str) -> float:
    prompt = (
        f"Query: {query}\n\nChunk:\n{chunk[:600]}\n\n"
        "Score relevance 0.0–1.0. Reply with a single decimal only."
    )
    r = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        return float(r.content.strip())
    except ValueError:
        return 0.0


async def score_context_quality(llm: ChatOpenAI, query: str, context: str) -> ContextQualityScore:
    prompt = (
        f"Query: {query}\n\nContext:\n{context[:2500]}\n\n"
        "Score sufficiency (0–1) and redundancy (0–1) of the context."
    )
    return await llm.with_structured_output(ContextQualityScore).ainvoke(
        [HumanMessage(content=prompt)]
    )


async def score_generation_quality(
    llm: ChatOpenAI, query: str, context: str
) -> GenerationQualityScore:
    prompt = (
        f"Answer using ONLY the context below. State if context is insufficient.\n\n"
        f"Query: {query}\n\nContext:\n{context[:2500]}"
    )
    return await llm.with_structured_output(GenerationQualityScore).ainvoke(
        [HumanMessage(content=prompt)]
    )


async def score_faithfulness(llm: ChatOpenAI, query: str, context: str, answer: str) -> FaithfulnessScore:
    prompt = (
        f"Query: {query}\n\nContext (ground truth):\n{context[:2500]}\n\n"
        f"Answer:\n{answer}\n\n"
        "Score faithfulness (0–1) and list any unsupported claims."
    )
    return await llm.with_structured_output(FaithfulnessScore).ainvoke(
        [HumanMessage(content=prompt)]
    )


# Main evaluation runner

async def run_rag_evaluation(retriever) -> Dict[str, Any]:
    
    print("RAG EVALUATION — 4 LAYERS")
    

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

    results = []
    for tc in RAG_TEST_CASES:
        query = tc["query"]
        docs = retriever.invoke(query)
        sources = [d.metadata.get("source", "") for d in docs]
        context = "\n\n---\n\n".join(d.page_content for d in docs)

        # asyncio.gather() is a function that allows you to run multiple asynchronous tasks concurrently and wait for all of them to finish.
        chunk_scores, cq = await asyncio.gather(
            asyncio.gather(*[score_chunk_relevance(llm, query, d.page_content) for d in docs]),
            score_context_quality(llm, query, context),
        )
        hit = any(any(exp in src for src in sources) for exp in tc["expected_sources"])
        avg_cr = sum(chunk_scores) / len(chunk_scores) if chunk_scores else 0.0

        gq = await score_generation_quality(llm, query, context)
        fq = await score_faithfulness(llm, query, context, gq.answer)

        short = query[:60] + "…" if len(query) > 60 else query
        status = "PASS" if hit else "FAIL"
        print(f"\n[{status}] {short}")
        print(f"  L1 Hit:{hit}  ChunkRel:{avg_cr:.2f}")
        print(f"  L2 Sufficiency:{cq.sufficiency:.2f}  Redundancy:{cq.redundancy:.2f}")
        print(f"  L3 Relevance:{gq.relevance:.2f}  Completeness:{gq.completeness:.2f}")
        print(f"  L4 Faithfulness:{fq.score:.2f}", end="")
        if fq.unsupported_claims:
            print(f"  {fq.unsupported_claims}")
        else:
            print("  grounded")

        results.append({
            "query": short,
            "hit": hit,
            "avg_chunk_relevance": avg_cr,
            "context_sufficiency": cq.sufficiency,
            "context_redundancy": cq.redundancy,
            "answer_relevance": gq.relevance,
            "answer_completeness": gq.completeness,
            "faithfulness": fq.score,
            "unsupported_claims": fq.unsupported_claims,
        })

    n = len(results)
    summary = {
        "hit_rate":            sum(r["hit"] for r in results) / n,
        "avg_chunk_relevance": sum(r["avg_chunk_relevance"] for r in results) / n,
        "context_sufficiency": sum(r["context_sufficiency"] for r in results) / n,
        "context_redundancy":  sum(r["context_redundancy"] for r in results) / n,
        "answer_relevance":    sum(r["answer_relevance"] for r in results) / n,
        "answer_completeness": sum(r["answer_completeness"] for r in results) / n,
        "faithfulness":        sum(r["faithfulness"] for r in results) / n,
    }
    print("RAG SUMMARY")
    for k, v in summary.items():
        fmt = f"{v:.0%}" if k == "hit_rate" else f"{v:.2f}"
        print(f"  {k:<20} {fmt}")
    return {"results": results, "summary": summary}
