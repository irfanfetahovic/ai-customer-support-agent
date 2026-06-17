---
title: AI Customer Support Agent
emoji: 🤖
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: "6.13.0"
app_file: app.py
pinned: false
---

# AI Customer Support Agent

![Python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

This is a fully functional AI customer support agent that handles customer enquiries automatically — answering questions about orders, refunds, shipping, warranties, and more — while staying accurate, professional, and safe. It connects to your knowledge base and a CRM data layer (simulated via an MCP server, swappable for a real CRM like Salesforce or Zendesk), remembers the full conversation, and checks the quality of its own answers before sending them. When it cannot resolve something, it says so clearly and escalates.

Built as a production-ready system: modular Python codebase, REST API, Gradio demo UI, automated test suite, and a full evaluation framework to measure quality before deployment.

---

## Business Value

**What this solves:**
- Customers waiting hours for a reply to a simple question ("where is my order?", "what is your refund policy?")
- Support agents spending the majority of their time on repetitive, low-complexity tickets
- Inconsistent responses when different agents handle the same question differently

**What you get:**
- **24/7 automated support** — handles routine enquiries instantly, around the clock, with no additional staffing cost
- **Consistent, on-brand answers** — every response is grounded in your own policies and knowledge base, not guessed by a generic chatbot
- **Safe and controllable** — the agent only answers questions related to customer support; off-topic or harmful messages are blocked before reaching the AI
- **Multi-turn conversations** — remembers context across a full conversation, so customers don't have to repeat themselves
- **Easy to update** — your FAQs, policies, and product information live in plain Markdown files; no code changes needed to update the agent's knowledge
- **Quality-checked responses** — a second AI agent reviews every answer before it is sent and requests a retry if the response is incomplete or off-tone
- **REST API included** — can be integrated into any existing website, app, or helpdesk platform

**Good fit for:** e-commerce businesses, SaaS companies, or any business with a high volume of repetitive support tickets and an existing set of policies or FAQs.

---

## Architecture Overview

The agent follows a **Planner → Worker → Evaluator** loop compiled as a LangGraph state machine. Each node has a single responsibility; routing between nodes is handled by conditional edges rather than monolithic prompts.


```
                       ┌─────────┐
         START ──────► │ Planner │
                       └────┬────┘
                            │  structured resolution plan
                       ┌────▼────┐
                  ┌───►│ Worker  │◄───┐
                  │    └────┬────┘    │
                  │         │         │
              (tool     (response  (re-route if
              calls)   drafted)    quality low)
                  │         │         │
                  │    ┌────▼─────┐   │
                  └────┤  Tools   │   │
                       │  (ToolNode)  │
                       └──────────┘   │
                                      │
                       ┌─────────────►┤
                       │   Evaluator  │
                       └─────┬────────┘
                             │
                    pass / needs_input
                             │
                            END
```

| Node | Role |
|---|---|
| **Planner** | Categorises the issue and generates a structured, step-by-step resolution plan. Never calls tools or speaks to the customer — separation of planning and execution. |
| **Worker** | Executes the plan using the full toolset: hybrid RAG retrieval and CRM lookups via MCP. Cites sources in every response. |
| **Tools (ToolNode)** | Standard LangGraph prebuilt node. Dispatches tool calls, collects results, and routes back to the worker. |
| **Evaluator** | Structured-output LLM judge. Scores the worker's reply against configurable success criteria and either approves the response or routes back to the worker for another attempt. |

---

## Key Technical Decisions

### Multi-Agent Design
The Planner–Worker–Evaluator separation enforces single-responsibility at the LLM level. The planner never has access to tools; the worker never decides whether its own answer is good enough. This separation reduces prompt complexity, improves reliability, and makes each node independently testable.

### Hybrid RAG Retrieval Pipeline
A plain FAISS vector search is fast but can miss exact-match queries. A BM25 lexical search catches keyword queries but misses semantic ones. This project combines both in an `EnsembleRetriever` (40% BM25, 60% FAISS), then applies **FlashrankRerank** cross-encoder reranking to the merged candidate set. This pipeline consistently outperforms either retriever alone on the evaluation test suite.

```
User query
    ├── BM25 (lexical)  → top-8 candidates
    └── FAISS (semantic, MMR) → top-8 candidates
              ↓
        EnsembleRetriever (merge + deduplicate)
              ↓
        FlashrankRerank cross-encoder → top-4 chunks
              ↓
        Worker context window
```

The FAISS index is persisted to disk and loaded on startup, avoiding redundant embedding API calls on every restart.

### Model Context Protocol (MCP) Integration
The CRM tooling is exposed over MCP (stdio transport) rather than being imported directly. This decouples the agent from the data layer: the MCP server can be swapped for a real CRM endpoint without changing agent code. An **explicit allowlist** (`MCP_TOOL_ALLOWLIST`) prevents the agent from calling any tool not approved at deployment time — even if the MCP server exposes additional tools in future.

### Three-Tier Security Guardrails
Security is applied in layers at increasing cost:

| Tier | Mechanism | Latency |
|---|---|---|
| **1 — Rule-based** | Compiled regex: detects prompt injection patterns, enforces input length cap (2,000 chars) | ~0 ms |
| **2 — Instruction hardening** | System prompt instructs the worker to refuse off-topic requests and never reveal internal configuration | In-flight |
| **3 — Moderation API** | Async call to `openai.moderations` flags harmful or policy-violating content | ~100 ms |

Cheap checks run first. The moderation API is only reached if the message clears tiers 1 and 2.

### Persistent Conversation Memory
Each conversation is identified by a UUID thread ID. LangGraph's `AsyncSqliteSaver` checkpointer persists the full message history to SQLite (`aiosqlite`), giving the agent true multi-turn memory across HTTP requests and server restarts. The async connection is managed via the FastAPI lifespan context manager to prevent connection leaks.

### Dual Evaluation Framework

**Online (runtime):** The Evaluator node runs inside every agent invocation. If `success_criteria_met` is `False` and `user_input_needed` is `False`, the graph re-routes back to the Worker for another attempt before returning a response. This is self-correcting quality control with zero external calls.

**Offline (pre-deployment):** Two evaluation modules in `src/evaluation/`:
- `rag_eval.py` — 4-layer RAG quality check: source hit rate, context sufficiency, redundancy score, and answer faithfulness (LLM-as-judge). Runs against 13 domain test cases.
- `e2e_eval.py` — Full pipeline evaluation: each test scenario is run through the compiled graph and scored by an LLM judge across 5 dimensions (resolution, accuracy, tone, completeness, scope adherence).

---

## Project Structure

```
├── api.py                        # FastAPI application (REST API)
├── app.py                        # Gradio demo UI
├── mcp_server/
│   └── server.py                 # MCP CRM server (customer profiles, order status)
├── src/
│   ├── config.py                 # All constants and env config in one place
│   ├── guardrails.py             # Input validation: regex + moderation API
│   ├── retriever.py              # Hybrid RAG pipeline: FAISS + BM25 + reranking
│   ├── mcp_client.py             # MCP server connection + tool allowlisting
│   ├── agent/
│   │   ├── state.py              # LangGraph TypedDict state + Pydantic EvaluatorOutput
│   │   ├── nodes.py              # Planner, Worker, Evaluator node functions + routers
│   │   └── graph.py              # Graph builder: nodes, edges, conditional routing
│   └── evaluation/
│       ├── rag_eval.py           # Offline RAG quality evaluation (4 layers)
│       └── e2e_eval.py           # Offline end-to-end agent evaluation (5 dimensions)
├── knowledge-base/               # Markdown knowledge base: FAQs, policies, playbooks
├── faiss_index/                  # Persisted FAISS vector index
├── notebooks/
│   └── customer_support.ipynb   # Development notebook with graph visualisation
├── scripts/
│   └── run_evaluation.py        # CLI runner for offline evaluation suite
└── tests/
    ├── unit/                     # Pure-function unit tests (guardrails, config, state)
    └── integration/              # Integration tests (retriever, MCP client)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM & Embeddings** | OpenAI `gpt-4o-mini`, `text-embedding-3-small` |
| **Agent framework** | LangGraph 0.2+, LangChain 0.3+ |
| **Vector search** | FAISS (persisted index) |
| **Lexical search** | BM25 (`rank-bm25`) |
| **Reranking** | FlashrankRerank cross-encoder |
| **Tool protocol** | Model Context Protocol (`mcp`, `langchain-mcp-adapters`) |
| **Guardrails** | Regex (compiled) + OpenAI Moderation API |
| **Persistent memory** | SQLite via `aiosqlite` + `langgraph-checkpoint-sqlite` |
| **REST API** | FastAPI + Uvicorn (async, with OpenAPI docs) |
| **Demo UI** | Gradio (Hugging Face Spaces compatible) |
| **Evaluation** | RAGAS + custom LLM-as-judge (RAG + E2E) |
| **Testing** | pytest + anyio (async test support) |
| **Packaging** | `uv` + `pyproject.toml` (PEP 517) |
| **Linting** | Ruff |

---

## Getting Started

### Prerequisites
- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) package manager
- OpenAI API key

### Installation

```bash
git clone https://github.com/your-username/ai-customer-support-agent.git
cd ai-customer-support-agent

# Install all dependencies
uv sync
```

### Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
```

### Running the REST API

```bash
uv run uvicorn api:app --reload
```

The API will be available at `http://localhost:8000`. Auto-generated interactive docs are at `http://localhost:8000/docs`.

### Running the Gradio Demo UI

```bash
uv run python app.py
```

### Running the Evaluation Suite

```bash
uv run python scripts/run_evaluation.py
```

### Running Tests

```bash
uv run pytest
```

---

## API Reference

### `POST /chat`

Send a message to the support agent. Supports multi-turn conversations via `thread_id`.

```json
{
  "message": "Where is my order ORD-1002?",
  "thread_id": "optional-uuid-to-continue-a-conversation",
  "success_criteria": "The customer's issue is fully resolved..."
}
```

**Response:**

```json
{
  "reply": "Your order ORD-1002 (Smartwatch X) is currently in transit...",
  "evaluator_feedback": "The response addresses the customer's query accurately...",
  "thread_id": "3f2a1b4c-...",
  "guardrail_triggered": false
}
```

### `GET /health`

Liveness check. Returns `agent_ready: true` once the graph has been initialised on startup.

### `POST /reset`

Returns a fresh `thread_id` to start a new conversation.

---

## Knowledge Base

The knowledge base in `knowledge-base/` is structured as plain Markdown files, making it easy to update without touching agent code. Categories:

- **FAQs** — General, shipping, refunds, warranty
- **Policies** — Privacy, refund, returns, shipping, warranty
- **Products** — Smartwatch X, Wireless Earbuds Pro
- **Troubleshooting** — Order tracking, payment issues, device-specific guides
- **Playbooks** — Account recovery, billing dispute, escalation procedures

To add or update content, edit the relevant `.md` file. The FAISS index will be rebuilt automatically on next startup if the `faiss_index/` directory is deleted.

---

## Docker

The FastAPI app is fully containerised using a two-stage Docker build: a `builder` stage that resolves and installs dependencies via `uv`, and a minimal `runtime` stage that runs the app as a non-root user.

### Build

```bash
docker build -t ai-customer-support-agent .
```

### Run

```bash
docker run --rm -p 8000:8000 \
  --env OPENAI_API_KEY=sk-... \
  ai-customer-support-agent
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

> **Never bake secrets into the image.** Pass `OPENAI_API_KEY` at runtime via `--env` or an env file (`--env-file .env`).

---

## Deployment

### Hugging Face Spaces

The Gradio app (`app.py`) is fully compatible with Hugging Face Spaces. Set `app_file: app.py` in the Space configuration and add `OPENAI_API_KEY` as a Space secret.

---

## Evaluation Results

Scores produced by an LLM-as-judge and committed to `results/latest.json` on every push to `main`.
Last run: **2026-06-16** · model: `gpt-4o-mini` · 22 RAG test cases · 9 E2E scenarios.

### RAG Pipeline

| Metric | Score | CI gate |
|---|---|---|
| Hit rate | 95.5% | — |
| Context sufficiency | 0.84 | ✅ |
| Answer relevance | 0.77 | ✅ |
| Answer completeness | 0.77 | — |
| Faithfulness | 0.77 | ✅ |
| Context redundancy | 0.00 | — |
| Avg chunk relevance | 0.47 | excluded¹ |

¹ Excluded from CI gate: individual chunks include lower-relevance noise alongside relevant ones, while context sufficiency (0.84) confirms the retrieved context as a whole is sufficient.

**Notable failures (4/22):** "order tracking delay", "payment failure", "international shipping costs", "Smartwatch X features", "Wireless Earbuds Pro battery life" — these cases returned 0.0 on all generation metrics. Investigation shows the KB content for these topics **does exist** and is detailed; two factors contributed to the low scores:

- **Stale FAISS index** — the index committed to the repo was built before some KB files were added/updated, causing retrieval misses ("order tracking" was the only case with `hit: false`). Fixed: `faiss_index/` is now excluded from git and rebuilt fresh in CI whenever the knowledge base changes.
- **LLM judge variance** — `gpt-4o-mini` occasionally scores 0.0 on content it correctly retrieved, producing false negatives in the evaluation. These scores are expected to improve after the index rebuild and may be further improved by switching the judge to `gpt-4o`or some other better model.

### End-to-End Agent

| Metric | Score |
|---|---|
| Overall | **0.95** |
| Accuracy | 1.00 |
| Scope adherence | 1.00 |
| Tone | 0.98 |
| Completeness | 0.97 |
| Resolution | 0.81 |

All 9 scenarios passed the 0.7 threshold. Resolution (0.81) is the lowest dimension — driven by the account recovery (0.80) and out-of-scope boundary (0.80) scenarios where the agent correctly declined or partially resolved rather than fully resolving.

---

## Design Principles

- **Separation of concerns at the LLM level** — each agent node has a single, narrow responsibility
- **Security by default** — guardrails are applied before the agent is reached; the allowlist is explicit and deny-by-default
- **Evaluation as a first-class concern** — quality is measured both at runtime (evaluator node) and offline (RAG + E2E eval suites)
- **Production code, not notebook code** — the core logic lives in importable Python modules with tests; the notebook is a development and demonstration artifact
- **Async throughout** — FastAPI, LangGraph nodes, MCP client, SQLite checkpointer, and moderation API calls are all fully async

---

## License

MIT
