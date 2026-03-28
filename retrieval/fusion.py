"""
fusion.py — Score normalization, fusion, and ranking for hybrid retrieval.

This module implements the canonical hybrid IR pipeline steps:
    normalize_scores → fuse_results → rank_results

Score normalization is extracted as a public, reusable function (fixes P2).

Implemented fusion strategies:

1. Reciprocal Rank Fusion (RRF):
   - From Cormack, Clarke & Buettcher (2009)
   - score(d) = Σ 1 / (k + rank_i(d))  for each system i
   - Parameter-light (only k), robust across domains
   - Does NOT require score normalization — only uses ranks
   - Preferred default for production systems

2. Weighted Linear Fusion:
   - score(d) = α * norm_lexical(d) + β * norm_semantic(d)
   - Requires min-max normalization of raw scores
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


# ---------------------------------------------------------------------------
# Score Normalization (Public — fixes P2)
# ---------------------------------------------------------------------------

def normalize_scores(
    results: List[Dict],
    method: str = "min_max",
) -> List[Dict]:
    """
    Normalizes scores in a result list to a [0, 1] range.

    This is an explicit, reusable step in the pipeline, separated from
    fusion logic so it can be applied, tested, and swapped independently.

    Args:
        results: List of {"doc_id": int, "score": float}.
        method: Normalization method. Currently supports "min_max".

    Returns:
        New list with normalized scores. Original list is not mutated.
    """
    if not results:
        return []

    scores = [r["score"] for r in results]

    if method == "min_max":
        min_s = min(scores)
        max_s = max(scores)
        range_s = max_s - min_s if max_s != min_s else 1.0
        return [
            {"doc_id": r["doc_id"], "score": (r["score"] - min_s) / range_s}
            for r in results
        ]
    else:
        raise ValueError(f"Unknown normalization method: '{method}'")


# ---------------------------------------------------------------------------
# Rank Results (Public — explicit ranking step)
# ---------------------------------------------------------------------------

def rank_results(results: List[Dict], top_k: int = 10) -> List[Dict]:
    """
    Sorts results by score descending and returns the top-k.

    This is an explicit step so that sorting is never implicit or repeated
    inside other functions. Acts as the final deterministic pass.

    Args:
        results: List of {"doc_id": int, "score": float}.
        top_k: Maximum number of results to return.

    Returns:
        Sorted list truncated to top_k.
    """
    sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
    return sorted_results[:top_k]


# ---------------------------------------------------------------------------
# Fusion Strategies
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    lexical_results: List[Dict],
    semantic_results: List[Dict],
    k: int = 60,
) -> List[Dict]:
    """
    Reciprocal Rank Fusion (RRF).

    For each document appearing in any result list, its fused score is:
        score(d) = Σ_i 1 / (k + rank_i(d))

    where rank_i(d) is the 1-based rank of document d in system i,
    and k is a smoothing constant (default 60, per the original paper).

    Note: RRF operates on RANKS, not scores. No score normalization needed.

    Args:
        lexical_results: BM25 results as [{"doc_id": int, "score": float}, ...]
        semantic_results: FAISS results as [{"doc_id": int, "score": float}, ...]
        k: RRF smoothing constant.

    Returns:
        Fused results (unsorted — call rank_results() after this).
    """
    rrf_scores: Dict[int, float] = defaultdict(float)

    for rank, result in enumerate(lexical_results, start=1):
        rrf_scores[result["doc_id"]] += 1.0 / (k + rank)

    for rank, result in enumerate(semantic_results, start=1):
        rrf_scores[result["doc_id"]] += 1.0 / (k + rank)

    return [
        {"doc_id": doc_id, "score": score}
        for doc_id, score in rrf_scores.items()
    ]


def weighted_fusion(
    lexical_results: List[Dict],
    semantic_results: List[Dict],
    lexical_weight: float = 0.3,
    semantic_weight: float = 0.7,
) -> List[Dict]:
    """
    Weighted linear fusion of pre-normalized scores.

    IMPORTANT: Expects results to be already normalized to [0, 1] via
    normalize_scores(). If raw scores are passed, the weighting will
    be meaningless because BM25 and FAISS use different score scales.

    Args:
        lexical_results: Normalized BM25 results.
        semantic_results: Normalized FAISS similarity results.
        lexical_weight: Weight α for lexical scores.
        semantic_weight: Weight β for semantic scores.

    Returns:
        Fused results (unsorted — call rank_results() after this).
    """
    lex_map = {r["doc_id"]: r["score"] for r in lexical_results}
    sem_map = {r["doc_id"]: r["score"] for r in semantic_results}

    all_ids = set(lex_map.keys()) | set(sem_map.keys())

    fused = []
    for doc_id in all_ids:
        lex_score = lex_map.get(doc_id, 0.0)
        sem_score = sem_map.get(doc_id, 0.0)
        combined = lexical_weight * lex_score + semantic_weight * sem_score
        fused.append({"doc_id": doc_id, "score": combined})

    return fused


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def fuse_results(
    lexical_results: List[Dict],
    semantic_results: List[Dict],
    strategy: str = None,
) -> List[Dict]:
    """
    Dispatches to the configured fusion strategy.

    For RRF: scores are NOT normalized (RRF uses ranks only).
    For Weighted: scores ARE normalized before fusion.

    Args:
        lexical_results: Results from BM25.
        semantic_results: Results from FAISS/NN.
        strategy: Override for the fusion strategy (defaults to config).

    Returns:
        Fused results (unsorted). Call rank_results() on the output.
    """
    strategy = strategy or ret_settings.FUSION_STRATEGY

    logger.info(f"Applying fusion strategy: {strategy}")

    if strategy == "rrf":
        return reciprocal_rank_fusion(
            lexical_results,
            semantic_results,
            k=ret_settings.RRF_K,
        )
    elif strategy == "weighted":
        # Weighted fusion REQUIRES normalized scores
        norm_lex = normalize_scores(lexical_results)
        norm_sem = normalize_scores(semantic_results)
        return weighted_fusion(
            norm_lex,
            norm_sem,
            lexical_weight=ret_settings.LEXICAL_WEIGHT,
            semantic_weight=ret_settings.SEMANTIC_WEIGHT,
        )
    else:
        raise ValueError(
            f"Unknown fusion strategy: '{strategy}'. "
            f"Supported: 'rrf', 'weighted'."
        )
