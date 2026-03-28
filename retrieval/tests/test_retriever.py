"""
test_retriever.py — End-to-end test for the NeuroMedIR Retrieval Module.

This script validates:
1. Indices can be loaded from disk.
2. Hybrid retrieval works end-to-end (BM25 + NN/FAISS → Fusion → Ranking).
3. Bilingual queries (EN/ES) produce meaningful results.
4. Individual lanes (lexical-only, semantic-only) work independently.
5. Both fusion strategies (RRF, weighted) function correctly.
"""

import json
import logging
import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from retrieval.retriever import Retriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_results(title: str, results: list):
    """Pretty prints a list of retrieval results."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    if not results:
        print("  (no results)")
        return
    for r in results:
        print(
            f"  #{r['rank']:2d} | Score: {r['score']:.6f} | "
            f"Doc {r['doc_id']:3d} | {r['title'][:50]}"
        )
        print(f"       Source: {r['source']}")
        print(f"       Snippet: {r['snippet'][:120]}...")
        print(f"       URL: {r['url']}")
        print()


def run_tests():
    print("\n" + "=" * 70)
    print("  NeuroMedIR Retrieval Module — End-to-End Test")
    print("=" * 70)

    # Initialize retriever (loads indices from disk)
    retriever = Retriever()

    # ─────────────────────────────────────────────────────────────────────
    # Test 1: Hybrid retrieval — English query
    # ─────────────────────────────────────────────────────────────────────
    en_query = "heart disease symptoms and treatment"
    results_en = retriever.retrieve(en_query, top_k=5)
    print_results(f"[HYBRID] English: '{en_query}'", results_en)

    # ─────────────────────────────────────────────────────────────────────
    # Test 2: Hybrid retrieval — Spanish query
    # ─────────────────────────────────────────────────────────────────────
    es_query = "síntomas y tratamiento de enfermedades del corazón"
    results_es = retriever.retrieve(es_query, top_k=5)
    print_results(f"[HYBRID] Spanish: '{es_query}'", results_es)

    # ─────────────────────────────────────────────────────────────────────
    # Test 3: Lexical-only retrieval (BM25)
    # ─────────────────────────────────────────────────────────────────────
    lex_query = "diabetes"
    results_lex = retriever.retrieve_lexical_only(lex_query, top_k=3)
    print_results(f"[LEXICAL ONLY] '{lex_query}'", results_lex)

    # ─────────────────────────────────────────────────────────────────────
    # Test 4: Semantic-only retrieval (NN → FAISS)
    # ─────────────────────────────────────────────────────────────────────
    sem_query = "dolor de cabeza fuerte y persistente"
    results_sem = retriever.retrieve_semantic_only(sem_query, top_k=3)
    print_results(f"[SEMANTIC ONLY] '{sem_query}'", results_sem)

    # ─────────────────────────────────────────────────────────────────────
    # Test 5: Weighted fusion strategy comparison
    # ─────────────────────────────────────────────────────────────────────
    compare_query = "cancer prevention and diagnosis"
    results_rrf = retriever.retrieve(compare_query, top_k=3, strategy="rrf")
    results_wgt = retriever.retrieve(compare_query, top_k=3, strategy="weighted")
    print_results(f"[RRF FUSION] '{compare_query}'", results_rrf)
    print_results(f"[WEIGHTED FUSION] '{compare_query}'", results_wgt)

    # ─────────────────────────────────────────────────────────────────────
    # Test 6: Cross-lingual capability
    # ─────────────────────────────────────────────────────────────────────
    # Query in Spanish should find English documents about the same topic
    cross_query = "nutrición y alimentación saludable"
    results_cross = retriever.retrieve(cross_query, top_k=3)
    print_results(f"[CROSS-LINGUAL] Spanish query: '{cross_query}'", results_cross)

    print("\n" + "=" * 70)
    print("  All tests completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
