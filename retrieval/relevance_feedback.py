"""
relevance_feedback.py — Rocchio-based relevance feedback for NeuroMedIR.

Adjusts the query vector in dense embedding space using explicit user feedback
(thumbs up / thumbs down on retrieved results) via the Rocchio algorithm:

    q_new = α·q_orig + β·mean(relevant_vectors) − γ·mean(irrelevant_vectors)

The adjusted vector is passed directly to FAISS search — no re-embedding of
the query text needed. Document vectors are obtained by re-encoding document
text at runtime (FAISS HNSW does not expose stored vectors for retrieval).

Usage (called from Retriever.retrieve_with_feedback):
    fb = RelevanceFeedback()
    new_results = fb.apply(
        query="síntomas de diabetes",
        feedback_map={42: True, 17: False, 88: True},
        retriever=retriever_instance,
    )

feedback_map format:
    {doc_id (int): relevant (bool), ...}
    True  → user marked as relevant   (positive example for Rocchio)
    False → user marked as irrelevant (negative example for Rocchio)
"""

import logging
import numpy as np
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from retrieval.retriever import Retriever

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rocchio default parameters
# ---------------------------------------------------------------------------
# α: weight of original query vector — keeps search anchored to intent
# β: weight of relevant doc centroid — pulls toward confirmed good docs
# γ: weight of irrelevant doc centroid — pushes away from bad docs
# Standard values from Rocchio (1971); γ < β to avoid over-penalizing.
ROCCHIO_ALPHA = 1.0
ROCCHIO_BETA  = 0.75
ROCCHIO_GAMMA = 0.25


class RelevanceFeedback:
    """
    Applies Rocchio relevance feedback to refine a query vector and
    re-executes semantic + hybrid retrieval with the adjusted vector.
    """

    def __init__(
        self,
        alpha: float = ROCCHIO_ALPHA,
        beta: float  = ROCCHIO_BETA,
        gamma: float = ROCCHIO_GAMMA,
    ):
        """
        Args:
            alpha: Weight for the original query vector.
            beta:  Weight for the centroid of relevant document vectors.
            gamma: Weight for the centroid of irrelevant document vectors.
        """
        self.alpha = alpha
        self.beta  = beta
        self.gamma = gamma

        logger.info(
            f"RelevanceFeedback ready — "
            f"α={self.alpha}, β={self.beta}, γ={self.gamma}"
        )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def apply(
        self,
        query: str,
        feedback_map: Dict[int, bool],
        retriever: "Retriever",
        top_k: int = None,
    ) -> List[Dict]:
        """
        Full feedback loop: encode query → adjust vector with Rocchio →
        re-run FAISS search → fuse with BM25 → enrich results.

        Args:
            query:        Original user query string.
            feedback_map: {doc_id: True/False} — True = relevant, False = not.
            retriever:    Live Retriever instance (provides encoder, index, store).
            top_k:        Number of results to return. Defaults to FINAL_TOP_K.

        Returns:
            Enriched result list in the same format as Retriever.retrieve().
        """
        from retrieval.configs import settings as ret_settings
        top_k = top_k or ret_settings.FINAL_TOP_K

        if not feedback_map:
            logger.debug("Empty feedback_map — running standard retrieve.")
            return retriever.retrieve(query, top_k=top_k)

        # Step 1: Encode the original query
        processed = retriever.preprocess_query(query)
        q_vector = retriever.generate_embedding(processed["semantic_text"])

        # Step 2: Separate relevant / irrelevant doc_ids
        relevant_ids   = [doc_id for doc_id, rel in feedback_map.items() if rel]
        irrelevant_ids = [doc_id for doc_id, rel in feedback_map.items() if not rel]

        # Step 3: Encode document texts for each group
        relevant_vectors   = self._encode_docs(relevant_ids,   retriever)
        irrelevant_vectors = self._encode_docs(irrelevant_ids, retriever)

        # Step 4: Rocchio adjustment
        adjusted_vector = self.adjust_query_vector(
            q_vector, relevant_vectors, irrelevant_vectors
        )

        # Step 5: FAISS search with the adjusted vector
        from retrieval.configs import settings as ret_settings
        semantic_results = retriever.search_faiss(
            adjusted_vector,
            top_k=ret_settings.SEMANTIC_TOP_K,
        )

        # Step 6: BM25 with original tokens (lexical lane unchanged)
        lexical_results = retriever.search_bm25(processed["lexical_tokens"])

        # Step 7: Fuse both lanes
        fused = retriever.fuse_results(lexical_results, semantic_results)
        ranked = retriever.rank_results(fused, top_k=ret_settings.RERANK_TOP_K)

        # Step 8: Re-rank with cross-encoder if available
        if retriever._reranker.is_enabled and ranked:
            doc_ids   = [r["doc_id"] for r in ranked]
            doc_texts = retriever._doc_store.get_texts(doc_ids)
            ranked = retriever._reranker.rerank(
                query=processed["raw"],
                results=ranked,
                doc_texts=doc_texts,
                top_k=top_k,
            )
            from retrieval.fusion import rank_results
            ranked = rank_results(ranked, top_k=top_k)
        else:
            ranked = ranked[:top_k]

        # Step 9: Enrich with metadata
        enriched = retriever._enrich_results(ranked)

        logger.info(
            f"Feedback applied — relevant: {len(relevant_ids)}, "
            f"irrelevant: {len(irrelevant_ids)} → {len(enriched)} results"
        )
        return enriched

    def adjust_query_vector(
        self,
        q_vector: np.ndarray,
        relevant_vectors: List[np.ndarray],
        irrelevant_vectors: List[np.ndarray],
    ) -> np.ndarray:
        """
        Computes the Rocchio-adjusted query vector.

        q_new = α·q_orig + β·mean(relevant) − γ·mean(irrelevant)

        If one group is empty its term is simply omitted (no penalty/boost).
        The result is L2-normalized to match the policy used at index time.

        Args:
            q_vector:           Original query embedding, shape (dim,).
            relevant_vectors:   List of relevant doc embeddings.
            irrelevant_vectors: List of irrelevant doc embeddings.

        Returns:
            Adjusted and L2-normalized query vector, shape (dim,).
        """
        adjusted = self.alpha * q_vector

        if relevant_vectors:
            rel_centroid = np.mean(np.stack(relevant_vectors, axis=0), axis=0)
            adjusted = adjusted + self.beta * rel_centroid

        if irrelevant_vectors:
            irrel_centroid = np.mean(np.stack(irrelevant_vectors, axis=0), axis=0)
            adjusted = adjusted - self.gamma * irrel_centroid

        # L2-normalize to match FAISSHNSWIndex._l2_normalize() applied at indexing
        norm = np.linalg.norm(adjusted)
        if norm > 1e-12:
            adjusted = adjusted / norm

        return adjusted

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _encode_docs(
        self,
        doc_ids: List[int],
        retriever: "Retriever",
    ) -> List[np.ndarray]:
        """
        Fetches document texts from the store and encodes them.

        Silently skips any doc_id whose text is missing or empty.

        Args:
            doc_ids:   List of document IDs to encode.
            retriever: Retriever instance (provides _doc_store and _encoder).

        Returns:
            List of embedding arrays, one per successfully encoded doc.
        """
        if not doc_ids:
            return []

        texts_map = retriever._doc_store.get_texts(doc_ids)
        vectors = []

        for doc_id in doc_ids:
            text = texts_map.get(doc_id, "")
            if not text:
                logger.debug(f"Feedback: no text for doc_id={doc_id}, skipping.")
                continue
            try:
                # Truncate to first 512 chars — enough for a representative vector
                vector = retriever.generate_embedding(text[:512])
                vectors.append(vector)
            except Exception as exc:
                logger.warning(f"Feedback: encoding failed for doc_id={doc_id}: {exc}")

        return vectors