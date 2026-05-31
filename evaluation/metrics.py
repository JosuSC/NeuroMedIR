"""
metrics.py — Evaluation metrics for NeuroMedIR retrieval quality.

Implements standard IR metrics:
    - Precision@k
    - Recall@k
    - F1@k
    - NDCG@k  (Normalized Discounted Cumulative Gain)
    - MRR     (Mean Reciprocal Rank)

All functions follow the same convention:
    - retrieved: ordered list of doc_ids returned by the system
    - relevant:  set of doc_ids marked as relevant for the query
    - k:         cutoff rank

Usage:
    from evaluation.metrics import precision_at_k, ndcg_at_k, mean_reciprocal_rank

    retrieved = [42, 17, 88, 3, 55]
    relevant  = {42, 88, 101}

    p  = precision_at_k(retrieved, relevant, k=5)   # 0.4
    r  = recall_at_k(retrieved, relevant, k=5)       # 0.667
    nd = ndcg_at_k(retrieved, relevant, k=5)         # depends on order
    rr = reciprocal_rank(retrieved, relevant)         # 1.0 (hit at rank 1)
"""

import math
import logging
from typing import List, Set, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-query metrics
# ---------------------------------------------------------------------------

def precision_at_k(retrieved: List[int], relevant: Set[int], k: int) -> float:
    """
    Fraction of top-k retrieved documents that are relevant.

    P@k = |retrieved[:k] ∩ relevant| / k

    Args:
        retrieved: Ordered list of doc_ids (rank 1 = first element).
        relevant:  Set of relevant doc_ids for this query.
        k:         Cutoff rank.

    Returns:
        Float in [0, 1].
    """
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / k


def recall_at_k(retrieved: List[int], relevant: Set[int], k: int) -> float:
    """
    Fraction of relevant documents found in the top-k results.

    R@k = |retrieved[:k] ∩ relevant| / |relevant|

    Args:
        retrieved: Ordered list of doc_ids.
        relevant:  Set of relevant doc_ids.
        k:         Cutoff rank.

    Returns:
        Float in [0, 1]. Returns 0.0 if relevant set is empty.
    """
    if not relevant or k <= 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / len(relevant)


def f1_at_k(retrieved: List[int], relevant: Set[int], k: int) -> float:
    """
    Harmonic mean of Precision@k and Recall@k.

    F1@k = 2 * P@k * R@k / (P@k + R@k)

    Returns 0.0 if both precision and recall are 0.
    """
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)
    if p + r == 0.0:
        return 0.0
    return 2 * p * r / (p + r)


def dcg_at_k(retrieved: List[int], relevant: Set[int], k: int) -> float:
    """
    Discounted Cumulative Gain at rank k (binary relevance).

    DCG@k = Σ_{i=1}^{k} rel_i / log2(i + 1)

    where rel_i = 1 if retrieved[i-1] in relevant, else 0.
    """
    dcg = 0.0
    for rank, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            dcg += 1.0 / math.log2(rank + 1)
    return dcg


def ndcg_at_k(retrieved: List[int], relevant: Set[int], k: int) -> float:
    """
    Normalized DCG at rank k.

    NDCG@k = DCG@k / IDCG@k

    IDCG is the DCG of a perfect ranking where all relevant docs
    appear at the top. Returns 0.0 if relevant set is empty.

    Args:
        retrieved: Ordered list of doc_ids.
        relevant:  Set of relevant doc_ids.
        k:         Cutoff rank.

    Returns:
        Float in [0, 1].
    """
    if not relevant or k <= 0:
        return 0.0

    actual_dcg = dcg_at_k(retrieved, relevant, k)

    # Ideal: place all relevant docs at the top ranks
    ideal_hits = min(len(relevant), k)
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))

    if ideal_dcg == 0.0:
        return 0.0

    return actual_dcg / ideal_dcg


def reciprocal_rank(retrieved: List[int], relevant: Set[int]) -> float:
    """
    Reciprocal rank of the first relevant document in the ranked list.

    RR = 1 / rank_of_first_hit

    Returns 0.0 if no relevant document appears in the list.
    """
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


# ---------------------------------------------------------------------------
# Aggregate metrics over a query set
# ---------------------------------------------------------------------------

def mean_reciprocal_rank(
    results_per_query: List[Dict],
) -> float:
    """
    Mean Reciprocal Rank over all queries.

    MRR = (1/|Q|) * Σ_q RR_q

    Args:
        results_per_query: List of dicts, each with:
            {
                "retrieved": [doc_id, ...],   # ordered
                "relevant":  {doc_id, ...},   # set
            }

    Returns:
        Float in [0, 1].
    """
    if not results_per_query:
        return 0.0
    rr_scores = [
        reciprocal_rank(q["retrieved"], q["relevant"])
        for q in results_per_query
    ]
    return sum(rr_scores) / len(rr_scores)


def evaluate_all(
    results_per_query: List[Dict],
    k: int = 10,
) -> Dict[str, float]:
    """
    Computes all metrics over a full query set and returns a summary dict.

    Args:
        results_per_query: List of dicts, each with:
            {
                "query_id":  str,
                "retrieved": [doc_id, ...],   # ordered list from retriever
                "relevant":  {doc_id, ...},   # set of relevant doc_ids
            }
        k: Cutoff rank for P@k, R@k, F1@k, NDCG@k.

    Returns:
        {
            "num_queries":   int,
            "precision@k":   float,
            "recall@k":      float,
            "f1@k":          float,
            "ndcg@k":        float,
            "mrr":           float,
            "k":             int,
        }
    """
    if not results_per_query:
        logger.warning("evaluate_all called with empty results list.")
        return {}

    p_scores, r_scores, f1_scores, ndcg_scores = [], [], [], []

    for q in results_per_query:
        retrieved = q["retrieved"]
        relevant  = q["relevant"]

        p_scores.append(precision_at_k(retrieved, relevant, k))
        r_scores.append(recall_at_k(retrieved, relevant, k))
        f1_scores.append(f1_at_k(retrieved, relevant, k))
        ndcg_scores.append(ndcg_at_k(retrieved, relevant, k))

    mrr = mean_reciprocal_rank(results_per_query)

    summary = {
        "num_queries": len(results_per_query),
        "precision@k": round(sum(p_scores)    / len(p_scores),    4),
        "recall@k":    round(sum(r_scores)    / len(r_scores),    4),
        "f1@k":        round(sum(f1_scores)   / len(f1_scores),   4),
        "ndcg@k":      round(sum(ndcg_scores) / len(ndcg_scores), 4),
        "mrr":         round(mrr, 4),
        "k":           k,
    }

    logger.info(
        f"Evaluation over {len(results_per_query)} queries @ k={k}: "
        f"P={summary['precision@k']}, R={summary['recall@k']}, "
        f"F1={summary['f1@k']}, NDCG={summary['ndcg@k']}, MRR={summary['mrr']}"
    )

    return summary