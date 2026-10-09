"""
Knowledge Base Retriever: Hybrid Search + Reranking
=====================================================

This implements the full retrieval pipeline:
1. BM25 (keyword search) — catches exact term matches
2. Dense embedding search (semantic) — catches meaning-based matches
3. Reciprocal Rank Fusion (RRF) — combines both result sets
4. Cross-encoder reranking — reorders by relevance

KEY CONCEPT - Hybrid Search:
BM25 is great at finding exact terms ("30-day return policy")
but misses synonyms ("refund window" means the same thing).
Dense embeddings catch semantic similarity but can miss
specific terms. Combining both gives the best of both worlds.

KEY CONCEPT - Reciprocal Rank Fusion (RRF):
When we have two ranked lists from BM25 and dense search,
RRF combines them: RRF_score = Σ 1/(k + rank_i)
Items ranked highly by BOTH methods get the highest combined score.
"""

import os
import warnings
import numpy as np
from typing import Optional

warnings.filterwarnings("ignore", category=FutureWarning)

from app.config import get_settings


# ============================================================
# Lazy-loaded components (heavy imports)
# ============================================================

_chroma_collection = None
_bm25_index = None
_bm25_documents = None
_reranker = None


def _get_chroma_collection():
    """Get or create the ChromaDB collection."""
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb
        settings = get_settings()
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _chroma_collection = client.get_or_create_collection(
            name="policies",
            metadata={"hnsw:space": "cosine"}
        )
    return _chroma_collection


def _get_bm25_index():
    """Get or create the BM25 index."""
    global _bm25_index, _bm25_documents
    if _bm25_index is None:
        from rank_bm25 import BM25Okapi
        collection = _get_chroma_collection()
        
        if collection.count() == 0:
            return None, []
        
        # Get all documents from ChromaDB
        all_docs = collection.get(include=["documents", "metadatas"])
        _bm25_documents = []
        tokenized_corpus = []
        
        for doc_text, metadata in zip(all_docs["documents"], all_docs["metadatas"]):
            _bm25_documents.append({
                "id": metadata.get("id", ""),
                "text": doc_text,
                "source": metadata.get("source", ""),
                "section": metadata.get("section", ""),
            })
            tokenized_corpus.append(doc_text.lower().split())
        
        if tokenized_corpus:
            _bm25_index = BM25Okapi(tokenized_corpus)
    
    return _bm25_index, _bm25_documents


def _get_reranker():
    """Lazy-load the cross-encoder reranker."""
    global _reranker
    if _reranker is None:
        settings = get_settings()
        if not settings.enable_reranker:
            return None
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            print(f"⚠️ Reranker load failed (non-fatal): {e}")
            return None
    return _reranker


# ============================================================
# Embedding function using Gemini
# ============================================================

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using Google Gemini API."""
    import google.generativeai as genai
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    result = genai.embed_content(
        model=settings.embedding_model,
        content=texts,
        task_type="retrieval_document",
    )
    return result["embedding"] if isinstance(result["embedding"][0], list) else [result["embedding"]]


def embed_query(query: str) -> list[float]:
    """Generate embedding for a search query."""
    import google.generativeai as genai
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    
    result = genai.embed_content(
        model=settings.embedding_model,
        content=query,
        task_type="retrieval_query",
    )
    return result["embedding"]


# ============================================================
# Reciprocal Rank Fusion
# ============================================================

def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],  # Each: [(doc_id, score), ...]
    k: int = 60,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """
    Combine multiple ranked lists using RRF.
    
    RRF formula: RRF_score(d) = Σ weight_i / (k + rank_i(d))
    
    Higher k = more trust in lower-ranked results.
    Default k=60 is standard in the literature.
    """
    if weights is None:
        settings = get_settings()
        weights = [settings.bm25_weight, settings.dense_weight]
    
    rrf_scores = {}
    
    for weight, ranked_list in zip(weights, ranked_lists):
        for rank, (doc_id, _score) in enumerate(ranked_list, 1):
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0.0
            rrf_scores[doc_id] += weight / (k + rank)
    
    # Sort by RRF score descending
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


# ============================================================
# Main Search Function
# ============================================================

def search_policies(query: str, top_k: int | None = None) -> list[dict]:
    """
    Full hybrid search pipeline:
    1. BM25 keyword search
    2. Dense embedding search (ChromaDB)
    3. Reciprocal Rank Fusion
    4. Cross-encoder reranking
    
    Returns list of policy chunks with scores and metadata.
    """
    settings = get_settings()
    if top_k is None:
        top_k = settings.rerank_top_k
    
    collection = _get_chroma_collection()
    if collection.count() == 0:
        return []
    
    candidates_k = settings.retrieval_top_k  # Get more candidates, then rerank down
    
    # --- Step 1: Dense embedding search ---
    try:
        query_embedding = embed_query(query)
        dense_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(candidates_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        
        dense_ranked = []
        if dense_results and dense_results["ids"] and dense_results["ids"][0]:
            for doc_id, distance in zip(dense_results["ids"][0], dense_results["distances"][0]):
                # ChromaDB cosine distance → similarity
                similarity = 1 - distance
                dense_ranked.append((doc_id, similarity))
    except Exception as e:
        print(f"⚠️ Dense search failed: {e}")
        dense_ranked = []
    
    # --- Step 2: BM25 keyword search ---
    bm25_ranked = []
    bm25_index, bm25_docs = _get_bm25_index()
    if bm25_index and bm25_docs:
        tokenized_query = query.lower().split()
        bm25_scores = bm25_index.get_scores(tokenized_query)
        
        # Get top-k BM25 results
        top_indices = np.argsort(bm25_scores)[::-1][:candidates_k]
        for idx in top_indices:
            if bm25_scores[idx] > 0:
                doc_id = bm25_docs[idx]["id"]
                bm25_ranked.append((doc_id, float(bm25_scores[idx])))
    
    # --- Step 3: Reciprocal Rank Fusion ---
    if dense_ranked and bm25_ranked:
        fused = reciprocal_rank_fusion([bm25_ranked, dense_ranked])
    elif dense_ranked:
        fused = dense_ranked
    elif bm25_ranked:
        fused = bm25_ranked
    else:
        return []
    
    # Get the top candidates
    candidate_ids = [doc_id for doc_id, _ in fused[:candidates_k]]
    
    # Fetch full documents for candidates
    if not candidate_ids:
        return []
    
    all_docs = collection.get(
        ids=candidate_ids,
        include=["documents", "metadatas"],
    )
    
    doc_map = {}
    for doc_id, doc_text, metadata in zip(all_docs["ids"], all_docs["documents"], all_docs["metadatas"]):
        doc_map[doc_id] = {
            "id": doc_id,
            "text": doc_text,
            "source": metadata.get("source", ""),
            "section": metadata.get("section", ""),
            "version": metadata.get("version", ""),
        }
    
    # --- Step 4: Reranking ---
    reranker = _get_reranker()
    if reranker and len(candidate_ids) > 1:
        # Cross-encoder scores each (query, document) pair
        pairs = [(query, doc_map[doc_id]["text"]) for doc_id in candidate_ids if doc_id in doc_map]
        rerank_scores = reranker.predict(pairs)
        
        # Sort by reranker score
        scored = list(zip(candidate_ids, rerank_scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in scored[:top_k]:
            if doc_id in doc_map:
                doc = doc_map[doc_id]
                doc["score"] = float(score)
                results.append(doc)
        return results
    else:
        # No reranker — use RRF scores
        results = []
        for doc_id, rrf_score in fused[:top_k]:
            if doc_id in doc_map:
                doc = doc_map[doc_id]
                doc["score"] = float(rrf_score)
                results.append(doc)
        return results
