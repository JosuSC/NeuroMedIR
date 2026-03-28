"""
neural_ranker.py — Neural scoring component for the retrieval pipeline.

Architecture role (from the user's spec):
    query → NN → embedding → FAISS
                              ↓
                            scores

This module wraps the neural encoder (SentenceTransformer) and the FAISS
vector index to produce semantic similarity scores for a given query.

It also provides an optional cross-encoder re-ranking stage for cases where
maximum precision is needed at the cost of latency.

Design decisions:
    1. The bi-encoder (SentenceTransformer) is used for fast initial retrieval
       via FAISS. This is the "NN → embedding" part of the architecture.
    2. The cross-encoder is an optional second pass that scores (query, doc)
       pairs directly for higher accuracy. Disabled by default for speed.
    3. We convert L2 distances from FAISS to similarity scores using
       score = 1 / (1 + L2_distance), giving a [0, 1] bounded score where
       higher is better, consistent with BM25's "higher is better" convention.
"""

import logging
import numpy as np
from typing import List, Dict, Optional

from indexing.multimodal.text_encoder import TextEncoder
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.configs import settings as idx_settings

logger = logging.getLogger(__name__)


class NeuralRanker:
    """
    Handles the neural/semantic scoring lane of the hybrid retrieval pipeline.
    """

    def __init__(
        self,
        encoder: TextEncoder,
        vector_index: FAISSHNSWIndex,
        cross_encoder_model: Optional[str] = None,
    ):
        """
        Args:
            encoder: The pre-loaded TextEncoder (shared with the indexer for consistency).
            vector_index: The pre-loaded FAISS HNSW index.
            cross_encoder_model: Optional HuggingFace model ID for cross-encoder re-ranking.
        """
        self.encoder = encoder
        self.vector_index = vector_index
        self.cross_encoder = None

        if cross_encoder_model:
            try:
                from sentence_transformers import CrossEncoder
                self.cross_encoder = CrossEncoder(cross_encoder_model)
                logger.info(f"Cross-encoder loaded: {cross_encoder_model}")
            except ImportError:
                logger.warning(
                    "sentence-transformers CrossEncoder not available. "
                    "Re-ranking disabled."
                )

    def score(
        self,
        semantic_text: str,
        top_k: int = 50,
    ) -> List[Dict]:
        """
        Generates semantic scores for a query using the neural embedding + FAISS pipeline.

        Flow: query_text → encoder → embedding → FAISS HNSW → L2 distances → similarity scores

        Args:
            semantic_text: Pre-processed query text (from QueryProcessor).
            top_k: Number of candidates to retrieve from the vector index.

        Returns:
            List of {"doc_id": int, "score": float} sorted by score descending.
            Score is in [0, 1] where 1 means identical.
        """
        if not semantic_text:
            return []

        # Encode query to dense vector using the neural network
        query_embedding = self.encoder.encode([semantic_text])[0]

        # Search FAISS HNSW for nearest neighbors
        raw_results = self.vector_index.search(
            query_embedding,
            top_k=top_k,
            ef_search=idx_settings.HNSW_EF_SEARCH,
        )

        # Convert L2 distances to similarity scores: score = 1 / (1 + d)
        # This maps [0, ∞) → (0, 1] — monotonically decreasing with distance
        scored = []
        for r in raw_results:
            sim_score = 1.0 / (1.0 + r["l2_distance"])
            scored.append({
                "doc_id": r["doc_id"],
                "score": sim_score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def rerank(
        self,
        query: str,
        doc_texts: Dict[int, str],
        candidate_ids: List[int],
        top_k: int = 20,
    ) -> List[Dict]:
        """
        Optional cross-encoder re-ranking for maximum precision.

        Instead of comparing embeddings, a cross-encoder takes (query, document)
        pairs as input and produces a direct relevance score. This is more
        accurate but O(n) in the number of candidates.

        Args:
            query: The raw query string.
            doc_texts: Mapping of doc_id → document text.
            candidate_ids: Doc IDs to re-rank (pre-filtered by the fusion stage).
            top_k: Maximum number of candidates to re-rank.

        Returns:
            List of {"doc_id": int, "score": float} sorted by score descending.
        """
        if self.cross_encoder is None:
            logger.debug("Cross-encoder not loaded; skipping re-rank.")
            return []

        # Limit candidates to top_k for cost control
        ids_to_rank = candidate_ids[:top_k]

        pairs = []
        valid_ids = []
        for doc_id in ids_to_rank:
            text = doc_texts.get(doc_id, "")
            if text:
                pairs.append((query, text))
                valid_ids.append(doc_id)

        if not pairs:
            return []

        # Cross-encoder scores each (query, doc) pair independently
        scores = self.cross_encoder.predict(pairs)

        results = []
        for doc_id, score in zip(valid_ids, scores):
            results.append({"doc_id": doc_id, "score": float(score)})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results
