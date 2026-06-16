import re
from typing import List

from langchain_core.documents import Document
from langchain_core.tools import Tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_compressors import FlashrankRerank
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import (
    KNOWLEDGE_BASE_DIR,
    FAISS_INDEX_PATH,
    EMBEDDING_MODEL,
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
)


def load_knowledge_documents() -> List[Document]:
    docs: List[Document] = []
    if not KNOWLEDGE_BASE_DIR.exists():
        return docs

    # rglob is a recursive glob function that finds all files in the directory and its subdirectories
    for file_path in sorted(KNOWLEDGE_BASE_DIR.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
            continue

        # Read the file content, ignoring encoding errors and stripping whitespace.
        content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            continue

        docs.append(
            Document(
                page_content=content,
                metadata={
                    "source": file_path.as_posix(),
                    "doc_type": file_path.suffix.lower().lstrip("."),
                },
            )
        )

    return docs


def build_customer_support_retriever():
    docs = load_knowledge_documents()
    if not docs:
        return None, 0, 0

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )

    # --- Persistence ---
    # Load the saved FAISS index if it exists, skipping embedding API calls.
    # Otherwise build it from scratch and save it for future runs.
    if FAISS_INDEX_PATH.exists():
        # allow_dangerous_deserialization is required because FAISS uses pickle internally.
        # This is safe here because the index is built and saved by this project only.
        vectorstore = FAISS.load_local(
            str(FAISS_INDEX_PATH), embeddings, allow_dangerous_deserialization=True
        )
        chunk_count = vectorstore.index.ntotal
        print(f"Loaded persisted FAISS index from '{FAISS_INDEX_PATH}' ({chunk_count} vectors)")
        # BM25 is not persisted to disk — re-split docs to rebuild it for hybrid search.
        chunks = splitter.split_documents(docs) if USE_HYBRID_SEARCH else None
    else:
        chunks = splitter.split_documents(docs)
        chunk_count = len(chunks)
        vectorstore = FAISS.from_documents(chunks, embeddings)
        vectorstore.save_local(str(FAISS_INDEX_PATH))
        print(f"Built and saved FAISS index to '{FAISS_INDEX_PATH}' ({chunk_count} chunks)")

    # --- Base retriever ---
    # Fetch more candidates than needed so the reranker has a meaningful pool to work with.
    # FAISS selects fetch_k candidates and then MMR selects the best k from that pool to return.
    faiss_retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": FAISS_K, "fetch_k": FAISS_FETCH_K},
    )

    if USE_HYBRID_SEARCH:
        # BM25 keyword retriever — complements semantic search for exact product names,
        # order IDs, error codes, and other keyword-heavy terms that embeddings can miss.
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = BM25_K

        # EnsembleRetriever merges both result sets via Reciprocal Rank Fusion (RRF).
        base_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever],
            weights=ENSEMBLE_WEIGHTS,
        )
        print("Using hybrid search (BM25 keyword + FAISS semantic)")
    else:
        base_retriever = faiss_retriever
        print("Using semantic-only search (FAISS with MMR)")

    # --- Reranking ---
    # FlashrankRerank uses a local cross-encoder model to re-score the candidates
    # by true query–passage relevance, then returns only the top_n results.
    if RERANKING_PROVIDER == "flashrank":
        reranker = FlashrankRerank(top_n=RERANKER_TOP_N)
        retriever = ContextualCompressionRetriever(
            base_compressor=reranker,
            base_retriever=base_retriever,
        )
    else:
        retriever = base_retriever

    return retriever, len(docs), chunk_count


def retrieve_customer_support_knowledge(query: str, retriever) -> str:
    """Retrieve relevant customer support knowledge with source citations."""
    if not query or not query.strip():
        return "Please provide a specific question or issue to search in the support knowledge base."

    if retriever is None:
        return (
            "Knowledge base is empty. Add .md or .txt files under knowledge-base/ "
            "and rebuild the retriever."
        )

    docs = retriever.invoke(query)
    if not docs:
        return "No relevant support knowledge found for this query."

    sections: List[str] = []
    for idx, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        # Preserve internal formatting (newlines, bullet points, numbered lists) so the worker
        # LLM can recognise and reproduce structured content such as multi-step guides.
        # Only collapse sequences of 3+ blank lines into a single blank line to avoid padding.
        snippet = doc.page_content.strip()
        snippet = re.sub(r"\n{3,}", "\n\n", snippet)
        # Truncate to the chunk size limit so full step lists are always included
        if len(snippet) > SNIPPET_MAX_LENGTH:
            snippet = snippet[:SNIPPET_MAX_LENGTH].rstrip() + "..."

        sections.append(f"[{idx}] Source: {source}\n{snippet}")

    return "\n\n".join(sections)


def build_retrieval_tool(retriever) -> Tool:
    """Factory that binds a built retriever to the retrieval tool."""
    def _retrieve(query: str) -> str:
        return retrieve_customer_support_knowledge(query, retriever)

    return Tool(
        name="retrieve_customer_support_knowledge",
        func=_retrieve,
        description=(
            "Retrieve grounded customer support knowledge from the local knowledge base. "
            "Use this before answering questions involving policy, troubleshooting steps, "
            "shipping, refunds, returns, warranty claims, billing disputes, "
            "account procedures, account recovery, login issues, password reset, "
            "or product behavior and troubleshooting."
        ),
    )
