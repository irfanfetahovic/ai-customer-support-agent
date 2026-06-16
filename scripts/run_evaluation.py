"""
Offline evaluation script for the AI Customer Support Agent.

Runs both evaluation suites from the command line — no Jupyter kernel required.
Suitable for use as a CI/CD gate.

Usage:
    python scripts/run_evaluation.py                    # run both suites
    python scripts/run_evaluation.py --suite rag        # RAG only
    python scripts/run_evaluation.py --suite e2e        # end-to-end only
    python scripts/run_evaluation.py --fail-threshold 0.7

Exit codes:
    0  all metrics are at or above the threshold
    1  one or more metrics are below the threshold, or an error occurred
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from src.retriever import build_customer_support_retriever
from src.evaluation.rag_eval import run_rag_evaluation
from src.evaluation.e2e_eval import run_e2e_evaluation

# Ensure the project root is on sys.path so local modules can be imported.

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)  # relative paths (knowledge-base/, faiss_index/) resolve correctly

load_dotenv(override=True)

# Main entry point

async def main(suite: str, fail_threshold: float, output_file: Optional[str]) -> int:
    retriever, doc_count, chunk_count = build_customer_support_retriever()
    if retriever is None:
        print("ERROR: No documents found in knowledge-base/. Aborting.")
        return 1

    print(f"Retriever ready — {doc_count} documents, {chunk_count} chunks.")

    all_results: Dict[str, Any] = {}
    failed = False

    if suite in ("rag", "both"):
        rag_results = await run_rag_evaluation(retriever)
        all_results["rag"] = rag_results
        s = rag_results["summary"]
        metrics_to_check = [s["avg_chunk_relevance"], s["context_sufficiency"],
                            s["answer_relevance"], s["faithfulness"]]
        if any(m < fail_threshold for m in metrics_to_check):
            print(f"\n⚠  RAG: one or more metrics below threshold {fail_threshold}")
            failed = True

    if suite in ("e2e", "both"):
        e2e_results = await run_e2e_evaluation(retriever)
        all_results["e2e"] = e2e_results
        if e2e_results["summary"]["overall"] < fail_threshold:
            print(f"\n⚠  E2E overall score {e2e_results['summary']['overall']:.2f} below threshold {fail_threshold}")
            failed = True

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            # E2EScores is a Pydantic model — serialise it before dumping
            json.dump(all_results, f, indent=2, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o))
        print(f"\nResults saved to {output_file}")

    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run offline evaluations for the customer support agent.")
    parser.add_argument("--suite", choices=["rag", "e2e", "both"], default="both",
                        help="Which evaluation suite to run (default: both)")
    parser.add_argument("--fail-threshold", type=float, default=0.7, metavar="THRESHOLD",
                        help="Exit with code 1 if any aggregate metric is below this value (default: 0.7)")
    parser.add_argument("--output", metavar="FILE",
                        help="Save results as JSON to this file path")
    args = parser.parse_args()

    exit_code = asyncio.run(main(args.suite, args.fail_threshold, args.output))
    sys.exit(exit_code)
