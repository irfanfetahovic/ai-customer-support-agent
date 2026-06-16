"""
Integration tests for src/retriever.py.

Tests are split into two groups:

  - No external dependencies: load_knowledge_documents and
    retrieve_customer_support_knowledge edge-case behaviour.
    These always run.

  - Requires OPENAI_API_KEY + built FAISS index: full retrieval pipeline.
    Skipped automatically when the key is absent.
"""

import os

import pytest

from src.config import FAISS_INDEX_PATH, KNOWLEDGE_BASE_DIR
from src.retriever import (
    build_customer_support_retriever,
    load_knowledge_documents,
    retrieve_customer_support_knowledge,
)

# pytest.mark is a factory for creating custom markers
# _NEEDS_OPENAI is a pytest marker/decorator object
_NEEDS_OPENAI = pytest.mark.skipif( 
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


# load_knowledge_documents — no API needed

class TestLoadKnowledgeDocuments:
    def test_returns_non_empty_list(self):
        docs = load_knowledge_documents()
        assert len(docs) > 0

    def test_every_doc_has_page_content(self):
        docs = load_knowledge_documents()
        for doc in docs:
            assert doc.page_content.strip(), f"Empty content for {doc.metadata.get('source')}"

    def test_every_doc_has_source_metadata(self):
        docs = load_knowledge_documents()
        for doc in docs:
            assert "source" in doc.metadata

    def test_all_knowledge_base_subdirs_represented(self):
        docs = load_knowledge_documents()
        sources = " ".join(doc.metadata["source"] for doc in docs)
        for subdir in ("faq", "policies", "products", "troubleshooting", "playbooks"):
            assert subdir in sources, f"No documents loaded from knowledge-base/{subdir}/"

    def test_only_supported_extensions_loaded(self):
        docs = load_knowledge_documents()
        for doc in docs:
            assert doc.metadata["doc_type"] in {"md", "txt"}



# retrieve_customer_support_knowledge — edge cases, no API needed

class TestRetrieveEdgeCases:
    def test_none_retriever_returns_helpful_message(self):
        result = retrieve_customer_support_knowledge("refund policy", None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_query_returns_helpful_message(self):
        # Pass a real retriever stub so the empty-query guard triggers first
        from unittest.mock import MagicMock
        result = retrieve_customer_support_knowledge("", MagicMock())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_whitespace_query_returns_helpful_message(self):
        from unittest.mock import MagicMock
        result = retrieve_customer_support_knowledge("   ", MagicMock())
        assert isinstance(result, str)
        assert len(result) > 0


# Full retrieval pipeline — requires OPENAI_API_KEY + FAISS index

class TestFullRetrievalPipeline:
    # Creating a class-scoped fixture called 'retriever' that builds the retriever once for all tests in this class.
    @pytest.fixture(scope="class")
    # retriever function will be executed before any test method in this class runs, and its return value will be passed to the test methods that accept a 'retriever' parameter.
    def retriever(self):
        if not FAISS_INDEX_PATH.exists():
            pytest.skip("FAISS index not built — run the notebook to build it first")
        r, _, _ = build_customer_support_retriever()
        return r

    @_NEEDS_OPENAI # decorator object returned by pytest.mark.skipif() factory
    def test_retriever_is_not_none(self, retriever):
        # parameter 'retriever' is the fixture defined above.
        assert retriever is not None
    # test_retriever_is_not_none = _NEEDS_OPENAI(test_retriever_is_not_none)

    @_NEEDS_OPENAI
    def test_relevant_query_returns_results(self, retriever):
        result = retrieve_customer_support_knowledge("How do I return a product?", retriever)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "No relevant" not in result

    @_NEEDS_OPENAI
    def test_result_contains_source_citation(self, retriever):
        result = retrieve_customer_support_knowledge("What is the refund policy?", retriever)
        # Results are formatted as "[1] Source: ..."
        assert "[1]" in result
        assert "Source:" in result

    @_NEEDS_OPENAI
    def test_shipping_query_returns_shipping_content(self, retriever):
        result = retrieve_customer_support_knowledge("How long does shipping take?", retriever)
        # Should surface content from the shipping policy or FAQ
        assert any(word in result.lower() for word in ("ship", "deliver", "transit"))

    @_NEEDS_OPENAI
    def test_nonsense_query_returns_no_results_message_or_low_relevance(self, retriever):
        # Retriever may return empty or very low-relevance results for junk input
        result = retrieve_customer_support_knowledge("xzqwerty1234nonsense", retriever)
        assert isinstance(result, str)
