import re
from pathlib import Path

from src.config import (
    PROJECT_ROOT,
    KNOWLEDGE_BASE_DIR,
    FAISS_INDEX_PATH,
    DB_PATH,
    EMBEDDING_MODEL,
    LLM_MODEL,
    SUPPORTED_KNOWLEDGE_EXTENSIONS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    USE_HYBRID_SEARCH,
    FAISS_K,
    FAISS_FETCH_K,
    BM25_K,
    ENSEMBLE_WEIGHTS,
    RERANKING_PROVIDER,
    RERANKER_TOP_N,
    SNIPPET_MAX_LENGTH,
    MCP_TOOL_ALLOWLIST,
    INPUT_MAX_LENGTH,
    INJECTION_PATTERNS,
    DEFAULT_SUCCESS_CRITERIA,
)


# Paths

class TestPaths:
    def test_project_root_is_path(self):
        assert isinstance(PROJECT_ROOT, Path)

    def test_project_root_exists(self):
        assert PROJECT_ROOT.exists()

    def test_knowledge_base_dir_is_under_project_root(self):
        assert KNOWLEDGE_BASE_DIR.parent == PROJECT_ROOT

    def test_faiss_index_path_is_under_project_root(self):
        assert FAISS_INDEX_PATH.parent == PROJECT_ROOT

    def test_db_path_is_string(self):
        assert isinstance(DB_PATH, str)

    def test_db_path_ends_with_db(self):
        assert DB_PATH.endswith(".db")


# Models

class TestModels:
    def test_embedding_model_is_string(self):
        assert isinstance(EMBEDDING_MODEL, str)
        assert len(EMBEDDING_MODEL) > 0

    def test_llm_model_is_string(self):
        assert isinstance(LLM_MODEL, str)
        assert len(LLM_MODEL) > 0



# RAG settings

class TestRagSettings:
    def test_supported_extensions_contains_md_and_txt(self):
        assert ".md" in SUPPORTED_KNOWLEDGE_EXTENSIONS
        assert ".txt" in SUPPORTED_KNOWLEDGE_EXTENSIONS

    def test_chunk_size_positive(self):
        assert CHUNK_SIZE > 0

    def test_chunk_overlap_less_than_chunk_size(self):
        assert CHUNK_OVERLAP < CHUNK_SIZE

    def test_chunk_overlap_non_negative(self):
        assert CHUNK_OVERLAP >= 0

    def test_use_hybrid_search_is_bool(self):
        assert isinstance(USE_HYBRID_SEARCH, bool)

    def test_faiss_k_positive(self):
        assert FAISS_K > 0

    def test_faiss_fetch_k_gte_faiss_k(self):
        assert FAISS_FETCH_K >= FAISS_K

    def test_bm25_k_positive(self):
        assert BM25_K > 0

    def test_ensemble_weights_sum_to_one(self):
        assert abs(sum(ENSEMBLE_WEIGHTS) - 1.0) < 1e-9

    def test_ensemble_weights_has_two_elements(self):
        assert len(ENSEMBLE_WEIGHTS) == 2

    def test_ensemble_weights_all_positive(self):
        assert all(w > 0 for w in ENSEMBLE_WEIGHTS)

    def test_reranking_provider_is_string(self):
        assert isinstance(RERANKING_PROVIDER, str)
        assert len(RERANKING_PROVIDER) > 0

    def test_reranker_top_n_positive(self):
        assert RERANKER_TOP_N > 0

    def test_reranker_top_n_lte_faiss_k(self):
        # After reranking we should return fewer docs than we fetched
        assert RERANKER_TOP_N <= FAISS_K

    def test_snippet_max_length_equals_chunk_size(self):
        assert SNIPPET_MAX_LENGTH == CHUNK_SIZE


# MCP

class TestMcpSettings:
    def test_allowlist_is_set(self):
        assert isinstance(MCP_TOOL_ALLOWLIST, set)

    def test_allowlist_contains_expected_tools(self):
        assert "lookup_customer_profile" in MCP_TOOL_ALLOWLIST
        assert "lookup_order_status" in MCP_TOOL_ALLOWLIST

    def test_allowlist_not_empty(self):
        assert len(MCP_TOOL_ALLOWLIST) > 0


# Guardrails

class TestGuardrailsSettings:
    def test_input_max_length_positive(self):
        assert INPUT_MAX_LENGTH > 0

    def test_injection_patterns_is_list(self):
        assert isinstance(INJECTION_PATTERNS, list)

    def test_injection_patterns_not_empty(self):
        assert len(INJECTION_PATTERNS) > 0

    def test_injection_patterns_all_valid_regex(self):
        for pattern in INJECTION_PATTERNS:
            compiled = re.compile(pattern)
            assert compiled is not None

    def test_injection_patterns_are_strings(self):
        assert all(isinstance(p, str) for p in INJECTION_PATTERNS)


# Gradio UI

class TestDefaultSuccessCriteria:
    def test_is_string(self):
        assert isinstance(DEFAULT_SUCCESS_CRITERIA, str)

    def test_not_empty(self):
        assert len(DEFAULT_SUCCESS_CRITERIA.strip()) > 0
