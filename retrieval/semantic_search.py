"""
semantic_search.py — Semantic retrieval via neural embeddings and FAISS.

Replaces the old neural_ranker.py with cleaner separation of concerns:
    1. generate_embedding(text) — Encode query text to dense vector via NN.
    2. search_faiss(vector) — Search the HNSW index for nearest neighbors.

Each function is independently callable and testable.

The L2-to-similarity conversion ensures that output scores follow the
"higher is better" convention consistent with BM25 scores.
"""

import logging
import numpy as np
from typing import List, Dict, Optional

from indexing.multimodal.text_encoder import TextEncoder
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.configs import settings as idx_settings

logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    Handles the semantic retrieval lane: NN → embedding → FAISS → scores.
    """

    def __init__(self, encoder: TextEncoder, vector_index: FAISSHNSWIndex):
        """
        Args:
            encoder: Pre-loaded TextEncoder (shared instance for consistency).
            vector_index: Pre-loaded FAISS HNSW index with document embeddings.
        """
        self.encoder = encoder
        self.vector_index = vector_index

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Encodes a text string into a dense vector using the neural network.

        This is the "NN → embedding" step of the pipeline.

        Args:
            text: Pre-processed query or document text.

        Returns:
            1-D numpy array of shape (embedding_dim,).

        Raises:
            ValueError: If text is empty.
        """
        if not text:
            raise ValueError("Cannot generate embedding for empty text.")

        embedding = self.encoder.encode([text])[0]
        return embedding

    def search_faiss(
        self,
        query_vector: np.ndarray,
        top_k: int = 50,
    ) -> List[Dict]:
        """
        Searches the FAISS HNSW index for nearest neighbors of the query vector.

        Converts L2 distances to similarity scores:
            score = 1 / (1 + L2_distance)
        This maps [0, ∞) → (0, 1] — monotonically decreasing with distance,
        where 1.0 means identical and values near 0 mean very dissimilar.

        Args:
            query_vector: Dense vector from generate_embedding().
            top_k: Number of candidates to retrieve.

        Returns:
            List of {"doc_id": int, "score": float} sorted by score descending.
        """
        raw_results = self.vector_index.search(
            query_vector,
            top_k=top_k,
            ef_search=idx_settings.HNSW_EF_SEARCH,
        )

        scored = []
        for r in raw_results:
            sim_score = 1.0 / (1.0 + r["l2_distance"])
            scored.append({
                "doc_id": r["doc_id"],
                "score": sim_score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def search(self, semantic_text: str, top_k: int = 50) -> List[Dict]:
        """
        Convenience method: generate_embedding + search_faiss in one call.

        Args:
            semantic_text: Pre-processed text from QueryProcessor.
            top_k: Number of candidates.

        Returns:
            List of {"doc_id": int, "score": float} sorted by score descending.
        """
        if not semantic_text:
            return []

        embedding = self.generate_embedding(semantic_text)
        return self.search_faiss(embedding, top_k=top_k)
