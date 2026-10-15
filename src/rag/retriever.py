"""
Semantic Retriever Module
-------------------------
Executes similarity search over ChromaDB vector embeddings.
Applies distance score thresholding, metadata filtering, and logs retrieval latency metrics.

Hybrid Search Enhancement:
  - Detects numeric ID / exact-value patterns in user queries (e.g., Transaction_ID: 100001).
  - After vector retrieval, performs a keyword scan on all retrieved chunk texts.
  - Exact-match chunks get a +0.4 score boost and are moved to the top of the results.
  - This fixes the "needle in a haystack" problem for exact ID lookups.
"""

import re
import time
from typing import List, Dict, Any, Optional
from src.vectorstore.vector_store import VectorStoreManager
from src.embeddings.embedder import EmbeddingManager
from src.utils.logger import logger
from src.utils.metrics import metrics_tracker
from config import TOP_K_RETRIEVAL, SIMILARITY_THRESHOLD

# Regex pattern: matches numeric IDs like 100001, alphanumeric IDs like CUST-001, SKU codes like ELX-001
_ID_PATTERN = re.compile(r'\b([A-Z]+-\d+|\d{4,})\b')

class SemanticRetriever:
    """Semantic vector retriever with hybrid exact-match re-ranking."""

    def __init__(self, vector_store: VectorStoreManager, embedding_manager: EmbeddingManager):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager

    def _extract_exact_keywords(self, query: str) -> List[str]:
        """
        Extracts exact numeric IDs and alphanumeric codes from query for keyword boosting.
        Examples: '100001', 'CUST-001', 'ELX-003', 'ACME-202'
        """
        matches = _ID_PATTERN.findall(query.upper())
        # Also extract any 4+ digit pure numbers not caught by uppercase match
        numbers = re.findall(r'\b\d{4,}\b', query)
        return list(set(matches + numbers))

    def _hybrid_rerank(self, results: List[Dict[str, Any]], exact_keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Re-ranks retrieved results by boosting chunks containing exact keyword matches.
        Exact-match chunks receive a +0.4 similarity score bonus so they rise to the top.
        """
        if not exact_keywords:
            return results

        boosted = []
        for result in results:
            text_upper = result["text"].upper()
            hit = any(kw in text_upper for kw in exact_keywords)
            if hit:
                # Boost score, cap at 1.0
                boosted_score = min(1.0, result["similarity_score"] + 0.40)
                boosted.append({**result, "similarity_score": boosted_score, "exact_match": True})
                logger.info(f"[HybridSearch] Exact keyword match → boosted chunk score to {boosted_score:.2f}")
            else:
                boosted.append({**result, "exact_match": False})

        # Sort by boosted score descending
        boosted.sort(key=lambda r: r["similarity_score"], reverse=True)
        return boosted

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K_RETRIEVAL,
        threshold: float = SIMILARITY_THRESHOLD,
        filter_file: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant vector chunks for a query string.
        Automatically applies hybrid keyword boosting for ID/exact-value queries.

        Args:
            query: User input query.
            top_k: Maximum chunks to retrieve.
            threshold: Minimum similarity score threshold.
            filter_file: Optional document filename filter.

        Returns:
            List of matching chunks with similarity scores and metadata, re-ranked.
        """
        start_time = time.time()

        where_clause = None
        if filter_file:
            where_clause = {"file_name": filter_file}

        # Detect exact ID/value patterns in the query for hybrid boosting
        exact_keywords = self._extract_exact_keywords(query)
        if exact_keywords:
            logger.info(f"[HybridSearch] Detected exact keyword patterns: {exact_keywords} — will boost exact-match chunks.")
            # Fetch more candidates so keyword boosting has a larger pool to re-rank from
            fetch_k = min(top_k * 4, self.vector_store.get_total_chunks())
        else:
            fetch_k = top_k

        # Query vector store for nearest neighbors
        raw_results = self.vector_store.query(
            query_text=query,
            embedding_manager=self.embedding_manager,
            top_k=max(fetch_k, top_k),
            where_filter=where_clause
        )

        # Apply similarity threshold filter
        filtered_results = [r for r in raw_results if r["similarity_score"] >= threshold]

        # Apply hybrid re-ranking: boost chunks with exact keyword matches to the top
        if exact_keywords:
            filtered_results = self._hybrid_rerank(filtered_results, exact_keywords)

        # Return only top_k after re-ranking
        final_results = filtered_results[:top_k]

        elapsed = time.time() - start_time
        metrics_tracker.record_retrieval(elapsed)

        logger.info(f"Retrieved {len(final_results)} / {len(raw_results)} relevant chunks in {elapsed:.4f}s for query: '{query}'")
        return final_results
