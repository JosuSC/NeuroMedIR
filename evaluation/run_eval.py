"""
run_eval.py — Evaluation runner for NeuroMedIR.

Loads test queries from evaluation/test_queries.json, runs the full
retrieval pipeline for each query, computes all IR metrics, and prints
a formatted report.

Usage:
    python -m evaluation.run_eval
    python -m evaluation.run_eval --k 5
    python -m evaluation.run_eval --k 10 --queries evaluation/test_queries.json

test_queries.json format:
    [
        {
            "query_id": "q01",
            "query":    "síntomas de diabetes tipo 2",
            "relevant": [42, 88, 101]    ← doc_ids marked as relevant
        },
        ...
    ]

Relevant doc_ids must be annotated manually after the corpus is built.
The script prints per-query results and an aggregate summary table.
"""

import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict

from retrieval.retriever import Retriever
from evaluation.metrics import evaluate_all, precision_at_k, recall_at_k, f1_at_k, ndcg_at_k, reciprocal_rank

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

DEFAULT_QUERIES_PATH = Path("evaluation/test_queries.json")
DEFAULT_K = 10


# ---------------------------------------------------------------------------
# Query set loader
# ---------------------------------------------------------------------------

def load_queries(path: Path) -> List[Dict]:
    """
    Loads and validates the test query set from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        List of query dicts with query_id, query, and relevant set.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If the format is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Test queries file not found: {path}\n"
            "Create it manually after the corpus is built. "
            "See the format in this file's docstring."
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("test_queries.json must be a JSON array.")

    queries = []
    for i, item in enumerate(raw):
        if "query" not in item:
            raise ValueError(f"Query at index {i} is missing the 'query' field.")
        if "relevant" not in item:
            raise ValueError(f"Query at index {i} is missing the 'relevant' field.")

        queries.append({
            "query_id":  item.get("query_id", f"q{i+1:02d}"),
            "query":     item["query"],
            "relevant":  set(item["relevant"]),
        })

    return queries


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_evaluation(
    queries: List[Dict],
    retriever: Retriever,
    k: int = DEFAULT_K,
) -> List[Dict]:
    """
    Runs the retrieval pipeline for each query and collects results.

    Args:
        queries:   List of query dicts from load_queries().
        retriever: Loaded Retriever instance.
        k:         Rank cutoff.

    Returns:
        List of result dicts ready for evaluate_all().
    """
    results = []

    for q in queries:
        try:
            retrieved_docs = retriever.retrieve(q["query"], top_k=k)
            retrieved_ids  = [doc["doc_id"] for doc in retrieved_docs]
        except Exception as exc:
            logger.error(f"Retrieval failed for query '{q['query']}': {exc}")
            retrieved_ids = []

        results.append({
            "query_id":  q["query_id"],
            "query":     q["query"],
            "retrieved": retrieved_ids,
            "relevant":  q["relevant"],
        })

    return results


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def print_report(results: List[Dict], k: int) -> None:
    """Prints a per-query breakdown and aggregate summary table."""
    sep = "-" * 80

    print(f"\n{'=' * 80}")
    print(f"  NeuroMedIR — Evaluation Report   (k={k})")
    print(f"{'=' * 80}\n")

    # Per-query table
    print(f"{'Query ID':<8} {'P@k':>6} {'R@k':>6} {'F1@k':>6} {'NDCG@k':>8} {'RR':>6}  Query")
    print(sep)

    for r in results:
        retrieved = r["retrieved"]
        relevant  = r["relevant"]
        p   = precision_at_k(retrieved, relevant, k)
        rec = recall_at_k(retrieved, relevant, k)
        f1  = f1_at_k(retrieved, relevant, k)
        nd  = ndcg_at_k(retrieved, relevant, k)
        rr  = reciprocal_rank(retrieved, relevant)
        query_preview = r["query"][:45] + "..." if len(r["query"]) > 45 else r["query"]
        print(f"{r['query_id']:<8} {p:>6.3f} {rec:>6.3f} {f1:>6.3f} {nd:>8.3f} {rr:>6.3f}  {query_preview}")

    print(sep)

    # Aggregate
    summary = evaluate_all(results, k=k)
    print(f"\n{'AGGREGATE':>8} {summary['precision@k']:>6.3f} {summary['recall@k']:>6.3f} "
          f"{summary['f1@k']:>6.3f} {summary['ndcg@k']:>8.3f} {summary['mrr']:>6.3f}\n")
    print(f"  Queries evaluated: {summary['num_queries']}")
    print(f"{'=' * 80}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run NeuroMedIR evaluation.")
    parser.add_argument(
        "--k", type=int, default=DEFAULT_K,
        help=f"Rank cutoff for metrics (default: {DEFAULT_K})"
    )
    parser.add_argument(
        "--queries", type=Path, default=DEFAULT_QUERIES_PATH,
        help=f"Path to test_queries.json (default: {DEFAULT_QUERIES_PATH})"
    )
    args = parser.parse_args()

    # Load queries
    print(f"Loading queries from {args.queries}...")
    queries = load_queries(args.queries)
    print(f"Loaded {len(queries)} queries.")

    # Load retriever
    print("Loading retriever from disk...")
    retriever = Retriever.from_disk()

    # Run
    print(f"Running evaluation (k={args.k})...\n")
    results = run_evaluation(queries, retriever, k=args.k)

    # Report
    print_report(results, k=args.k)


if __name__ == "__main__":
    main()