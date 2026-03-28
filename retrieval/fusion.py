"""
fusion.py — Score fusion strategies for hybrid retrieval.

This module combines results from the lexical (BM25) and semantic (FAISS/NN)
retrieval lanes into a single unified ranking.

Why fusion matters:
    BM25 excels at exact keyword matching (e.g., drug names, ICD codes).
    Neural search excels at understanding intent and synonyms across languages.
    Neither alone is sufficient for medical IR — fusion gives us both strengths.

Implemented strategies:

1. Reciprocal Rank Fusion (RRF):
   - From Cormack, Clarke & Buettcher (2009)
   - score(d) = Σ 1 / (k + rank_i(d))  for each system i
   - Parameter-light (only k), robust across domains
   - Does NOT require score normalization — only uses ranks
   - Preferred default for production systems

2. Weighted Linear Fusion:
   - score(d) = α * norm_lexical(d) + β * norm_semantic(d)
   - Requires careful min-max normalization of raw scores
   - α + β = 1.0, configurable in settings
   - More tunable but more fragile than RRF

Design decision:
    RRF is the default because it's proven to be robust without
    per-query parameter tuning, which is essential for a system
    that handles two languages and heterogeneous medical content.
"""

import logging
from typing import List, Dict
from collections import defaultdict

from .configs import settings as ret_settings

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    lexical_results: List[Dict],
    semantic_results: List[Dict],
    k: int = 60,
    top_k: int = 10,
) -> List[Dict]:
    """
    Reciprocal Rank Fusion (RRF).

    For each document appearing in any result list, its fused score is:
        score(d) = Σ_i 1 / (k + rank_i(d))

    where rank_i(d) is the 1-based rank of document d in system i,
    and k is a smoothing constant (default 60, per the original paper).

    Args:
        lexical_results: BM25 results as [{"doc_id": int, "score": float}, ...]
        semantic_results: FAISS results as [{"doc_id": int, "score": float}, ...]
        k: RRF smoothing constant.
        top_k: Number of final results to return.

    Returns:
        Fused results sorted by RRF score descending.
    """
    rrf_scores: Dict[int, float] = defaultdict(float)

    # Lexical lane contribution
    for rank, result in enumerate(lexical_results, start=1):
        doc_id = result["doc_id"]
        rrf_scores[doc_id] += 1.0 / (k + rank)

    # Semantic lane contribution
    for rank, result in enumerate(semantic_results, start=1):
        doc_id = result["doc_id"]
        rrf_scores[doc_id] += 1.0 / (k + rank)

    # Sort by fused score
    fused = [
        {"doc_id": doc_id, "score": score}
        for doc_id, score in rrf_scores.items()
    ]
    fused.sort(key=lambda x: x["score"], reverse=True)

    return fused[:top_k]


def weighted_fusion(
    lexical_results: List[Dict],
    semantic_results: List[Dict],
    lexical_weight: float = 0.3,
    semantic_weight: float = 0.7,
    top_k: int = 10,
) -> List[Dict]:
    """
    Weighted linear fusion with min-max score normalization.

    Steps:
    1. Normalize scores from each lane to [0, 1] via min-max scaling.
    2. Compute: score(d) = α * norm_lex(d) + β * norm_sem(d)
    3. Sort by fused score.

    Args:
        lexical_results: BM25 results.
        semantic_results: FAISS similarity results.
        lexical_weight: Weight α for lexical scores.
        semantic_weight: Weight β for semantic scores.
        top_k: Number of final results.

    Returns:
        Fused results sorted by weighted score descending.
    """
    def _min_max_normalize(results: List[Dict]) -> Dict[int, float]:
        """Normalizes scores to [0, 1] range."""
        if not results:
            return {}
        scores = [r["score"] for r in results]
        min_s = min(scores)
        max_s = max(scores)
        range_s = max_s - min_s if max_s != min_s else 1.0
        return {
            r["doc_id"]: (r["score"] - min_s) / range_s
            for r in results
        }

    norm_lex = _min_max_normalize(lexical_results)
    norm_sem = _min_max_normalize(semantic_results)

    # Union of all doc IDs
    all_ids = set(norm_lex.keys()) | set(norm_sem.keys())

    fused = []
    for doc_id in all_ids:
        lex_score = norm_lex.get(doc_id, 0.0)
        sem_score = norm_sem.get(doc_id, 0.0)
        combined = lexical_weight * lex_score + semantic_weight * sem_score
        fused.append({"doc_id": doc_id, "score": combined})

    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused[:top_k]


def fuse(
    lexical_results: List[Dict],
    semantic_results: List[Dict],
    strategy: str = None,
    top_k: int = None,
) -> List[Dict]:
    """
    Dispatches to the configured fusion strategy.

    Args:
        lexical_results: Results from BM25.
        semantic_results: Results from FAISS/NN.
        strategy: Override for the fusion strategy (defaults to config).
        top_k: Override for number of final results (defaults to config).

    Returns:
        Fused and ranked results.
    """
    strategy = strategy or ret_settings.FUSION_STRATEGY
    top_k = top_k or ret_settings.FINAL_TOP_K

    logger.info(f"Applying fusion strategy: {strategy} (top_k={top_k})")

    if strategy == "rrf":
        return reciprocal_rank_fusion(
            lexical_results,
            semantic_results,
            k=ret_settings.RRF_K,
            top_k=top_k,
        )
    elif strategy == "weighted":
        return weighted_fusion(
            lexical_results,
            semantic_results,
            lexical_weight=ret_settings.LEXICAL_WEIGHT,
            semantic_weight=ret_settings.SEMANTIC_WEIGHT,
            top_k=top_k,
        )
    else:
        raise ValueError(
            f"Unknown fusion strategy: '{strategy}'. "
            f"Supported: 'rrf', 'weighted'."
        )
