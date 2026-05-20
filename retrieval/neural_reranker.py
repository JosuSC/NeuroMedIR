"""
neural_reranker.py — Cross-Encoder Neural Re-ranker for Stage 2 Precision.

Implements the second stage of the 3-stage retrieval architecture:

    Stage 1 (Recall):  BM25 + FAISS + RRF → top-k candidates (k=50-100)
    Stage 2 (Precision): Cross-Encoder re-ranks (query, doc) pairs  ← THIS MODULE
    Stage 3 (Re-ordering): Documents sorted by cross-encoder scores

The cross-encoder takes (query, document_text) pairs as input and produces
a single relevance score per pair. Unlike bi-encoders that encode query and
document independently, cross-encoders perform full self-attention across
both inputs, capturing fine-grained query-document interactions.

Reference:
    Nogueira & Cho (2019) — "Passage Re-ranking with BERT"
    Nogueira et al. (2020) — "Document Ranking with a Pretrained Sequence-to-Sequence Model"

Design decisions:
    - Lazy loading: The model is NOT loaded at import time; it loads on first
      call to rerank() to avoid slowing startup when re-ranking is disabled.
    - Batched inference: Processes (query, doc) pairs in mini-batches to
      balance GPU/CPU memory usage vs. throughput.
    - Graceful degradation: If the model fails to load, returns the input
      results unchanged with a warning log.
    - Device auto-detection: Uses CUDA if available, falls back to CPU.
"""

import logging
from typing import List, Dict, Optional

from sentence_transformers import CrossEncoder

from .configs import settings as ret_settings

logger = logging.getLogger(__name__)


class NeuralReranker:
    """
    Cross-Encoder re-ranker that refines hybrid retrieval results.

    Takes the top-k candidates from Stage 1 (BM25+FAISS+RRF fusion) and
    re-scores each (query, document) pair using a cross-encoder model.
    The cross-encoder's self-attention over the concatenated [query, doc]
    sequence captures lexical-semantic interactions that bi-encoders miss.

    Usage:
        reranker = NeuralReranker()
        reranked = reranker.rerank(
            query="síntomas de diabetes tipo 2",
            results=[{"doc_id": 1, "score": 0.85}, {"doc_id": 2, "score": 0.72}],
            doc_texts={1: "La diabetes tipo 2...", 2: "Otros síntomas..."},
            top_k=20
        )
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        max_length: int = 512,
        batch_size: int = 32,
        device: Optional[str] = None,
    ):
        """
        Args:
            model_name: HuggingFace cross-encoder model identifier.
                        Defaults to settings.CROSS_ENCODER_MODEL.
                        If None in settings, re-ranking is disabled.
            max_length: Maximum token length for (query, doc) pairs.
                        Documents exceeding this are truncated.
            batch_size: Number of (query, doc) pairs per inference batch.
                        Lower values use less memory; higher values are faster.
            device: Device string ("cuda", "cpu", "cuda:0", etc.).
                    Auto-detected if None.
        """
        self._model_name = model_name or ret_settings.CROSS_ENCODER_MODEL
        self._max_length = max_length
        self._batch_size = batch_size
        self._device = device
        self._model: Optional[CrossEncoder] = None
        self._loaded = False

        if self._model_name is None:
            logger.info(
                "NeuralReranker: CROSS_ENCODER_MODEL is None — "
                "re-ranking DISABLED. Set it in retrieval/configs/settings.py "
                "to enable (e.g., 'cross-encoder/ms-marco-MiniLM-L-6-v2')."
            )
        else:
            logger.info(
                f"NeuralReranker: Will load model '{self._model_name}' "
                f"on first rerank() call (lazy loading)."
            )

    # -------------------------------------------------------------------
    # Lazy model loading
    # -------------------------------------------------------------------

    def _load_model(self) -> bool:
        """
        Loads the cross-encoder model into memory (lazy, called once).

        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self._loaded:
            return self._model is not None

        if self._model_name is None:
            logger.warning("NeuralReranker: Cannot load — CROSS_ENCODER_MODEL is None.")
            self._loaded = True
            return False

        try:
            logger.info(f"Loading cross-encoder model: {self._model_name}...")
            self._model = CrossEncoder(
                self._model_name,
                max_length=self._max_length,
                device=self._device,
            )
            self._loaded = True
            logger.info(
                f"Cross-encoder loaded successfully. "
                f"Device: {self._model.device}, "
                f"Max length: {self._max_length}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to load cross-encoder model '{self._model_name}': {e}. "
                f"Re-ranking will be skipped."
            )
            self._loaded = True  # Don't retry on every call
            self._model = None
            return False

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        """Returns True if re-ranking is configured and model is available."""
        if self._model_name is None:
            return False
        if self._loaded:
            return self._model is not None
        return True  # Not loaded yet but configured — will try on first use

    @property
    def model_name(self) -> Optional[str]:
        """Returns the configured model name."""
        return self._model_name

    def rerank(
        self,
        query: str,
        results: List[Dict],
        doc_texts: Dict[int, str],
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """
        Re-ranks retrieval results using the cross-encoder.

        For each candidate document, constructs the (query, document_text) pair,
        runs it through the cross-encoder, and replaces the fusion score with
        the cross-encoder's relevance score. Results are then sorted by the
        new scores in descending order.

        Args:
            query: The original user query string.
            results: Fused results from Stage 1, each with "doc_id" and "score".
            doc_texts: Mapping of doc_id → document text (from DocumentStore).
            top_k: Number of top results to return after re-ranking.
                   Defaults to settings.RERANK_TOP_K.

        Returns:
            Re-ranked list of {"doc_id": int, "score": float} sorted by
            cross-encoder relevance score descending. If re-ranking is
            disabled or fails, returns the input results unchanged.
        """
        top_k = top_k or ret_settings.RERANK_TOP_K

        # Guard: no model configured → pass through
        if self._model_name is None:
            logger.debug("NeuralReranker: Skipping — model not configured.")
            return results[:top_k]

        # Guard: empty results
        if not results:
            return []

        # Lazy load the model
        if not self._loaded:
            self._load_model()

        if self._model is None:
            logger.warning("NeuralReranker: Model not available — returning original results.")
            return results[:top_k]

        # Build (query, document_text) pairs
        pairs = []
        valid_results = []
        for result in results:
            doc_id = result["doc_id"]
            doc_text = doc_texts.get(doc_id, "")

            if not doc_text:
                logger.debug(f"NeuralReranker: No text for doc_id={doc_id}, skipping.")
                continue

            # Truncate document text to avoid exceeding max_length
            # Rough heuristic: ~4 chars per token, reserve ~64 tokens for query
            max_doc_chars = (self._max_length - 64) * 4
            if len(doc_text) > max_doc_chars:
                doc_text = doc_text[:max_doc_chars]

            pairs.append((query, doc_text))
            valid_results.append(result)

        if not pairs:
            logger.warning("NeuralReranker: No valid (query, doc) pairs — returning original results.")
            return results[:top_k]

        # Run cross-encoder inference in batches
        logger.info(
            f"NeuralReranker: Re-ranking {len(pairs)} candidates "
            f"(batch_size={self._batch_size}, top_k={top_k})..."
        )

        try:
            ce_scores = self._model.predict(
                pairs,
                batch_size=self._batch_size,
                show_progress_bar=False,
            )
        except Exception as e:
            logger.error(f"NeuralReranker: Inference failed: {e}. Returning original results.")
            return results[:top_k]

        # Replace scores with cross-encoder scores
        reranked = []
        for result, ce_score in zip(valid_results, ce_scores):
            reranked.append({
                "doc_id": result["doc_id"],
                "score": float(ce_score),
                "fusion_score": result["score"],  # Preserve original fusion score
            })

        # Sort by cross-encoder score descending
        reranked.sort(key=lambda x: x["score"], reverse=True)

        # Truncate to top_k
        reranked = reranked[:top_k]

        logger.info(
            f"NeuralReranker: Done. Top score: {reranked[0]['score']:.4f}, "
            f"Bottom score: {reranked[-1]['score']:.4f} "
            f"(from {len(pairs)} candidates)"
        )

        return reranked

    def rerank_with_metadata(
        self,
        query: str,
        results: List[Dict],
        doc_texts: Dict[int, str],
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """
        Re-ranks and preserves ALL original metadata (title, snippet, etc.).

        This is a convenience method that combines rerank() with metadata
        preservation. Use this when you need enriched results with both
        cross-encoder scores and document metadata.

        Args:
            query: The original user query string.
            results: Enriched results (with title, snippet, etc.).
            doc_texts: Mapping of doc_id → document text.
            top_k: Number of top results to return.

        Returns:
            Re-ranked enriched results with updated scores.
        """
        top_k = top_k or ret_settings.RERANK_TOP_K

        # Extract minimal format for re-ranking
        minimal_results = [
            {"doc_id": r["doc_id"], "score": r["score"]}
            for r in results
        ]

        reranked = self.rerank(query, minimal_results, doc_texts, top_k=top_k)

        # Merge back into original enriched results
        enriched = []
        for r in reranked:
            # Find the original enriched result
            original = next(
                (orig for orig in results if orig["doc_id"] == r["doc_id"]),
                None
            )
            if original:
                enriched.append({
                    **original,
                    "score": round(r["score"], 6),
                    "fusion_score": r.get("fusion_score", original["score"]),
                })
            else:
                enriched.append(r)

        return enriched

    # -------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "loaded" if self._model is not None else "not loaded"
        model = self._model_name or "None (disabled)"
        return f"NeuralReranker(model='{model}', status={status})"

