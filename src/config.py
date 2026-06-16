from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)


# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge-base"
FAISS_INDEX_PATH = PROJECT_ROOT / "faiss_index"
DB_PATH = str(PROJECT_ROOT / "memory.db")

# Models
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"

# RAG — document loading
SUPPORTED_KNOWLEDGE_EXTENSIONS = {".md", ".txt"}

# RAG — chunking
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120

# RAG — retrieval
USE_HYBRID_SEARCH = True
FAISS_K = 8
FAISS_FETCH_K = 20
BM25_K = 8
ENSEMBLE_WEIGHTS = [0.4, 0.6]  # [BM25 weight, FAISS weight]

# RAG — reranking
RERANKING_PROVIDER = "flashrank"
RERANKER_TOP_N = 4

# RAG — snippet truncation
# Matches CHUNK_SIZE so a full chunk is always returned to the worker.
SNIPPET_MAX_LENGTH = CHUNK_SIZE

# MCP
MCP_TOOL_ALLOWLIST = {"lookup_customer_profile", "lookup_order_status"}

# Guardrails
INPUT_MAX_LENGTH = 2000

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"forget\s+(all\s+)?instructions",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(?!a?\s*customer\b)",
    r"jailbreak",
    r"prompt\s*injection",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions|tools)",
]

# Gradio UI
DEFAULT_SUCCESS_CRITERIA = (
    "The customer's issue is fully resolved or clearly addressed. "
    "The response is accurate, empathetic, and professional. "
    "All parts of the customer's question are answered. "
    "If the issue cannot be resolved, escalation to a human agent is offered."
)
