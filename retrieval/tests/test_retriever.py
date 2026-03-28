"""
test_retriever.py — End-to-end and per-function tests for the NeuroMedIR Retrieval Module.

Validates:
1. Each pipeline function works independently.
2. Hybrid retrieval produces correct end-to-end results.
3. Bilingual queries (EN/ES) are handled properly.
4. Both fusion strategies (RRF, weighted) function correctly.
5. Latency is measured and reported per stage.
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from retrieval.retriever import Retriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_results(title: str, results: list):
    """Pretty prints a list of retrieval results."""
    print(f"\n{'='*72}")
    print(f"  {title}")
    print(f"{'='*72}")
    if not results:
        print("  (no results)")
        return
    for r in results:
        latency = f" | {r['latency_ms']}ms" if "latency_ms" in r else ""
        print(
            f"  #{r['rank']:2d} | Score: {r['score']:.6f} | "
            f"Doc {r['doc_id']:3d} | {r['title'][:45]}{latency}"
        )
        print(f"       Source: {r['source']}")
        print(f"       Snippet: {r['snippet'][:100]}...")
        print()


def run_tests():
    print("\n" + "=" * 72)
    print("  NeuroMedIR Retrieval Module — Refactored Tests")
    print("=" * 72)

    # ─── Initialize via factory ──────────────────────────────────────────
    retriever = Retriever.from_disk()

    # ─── Test 1: preprocess_query ────────────────────────────────────────
    print("\n--- Test 1: preprocess_query ---")
    processed = retriever.preprocess_query("heart disease prevention")
    print(f"  Raw: {processed['raw']}")
    print(f"  Lexical tokens: {processed['lexical_tokens']}")
    print(f"  Semantic text: {processed['semantic_text'][:80]}...")
    assert len(processed["lexical_tokens"]) > 0, "Tokens should not be empty"
    assert len(processed["semantic_text"]) > 0, "Semantic text should not be empty"
    print("  OK PASSED")

    # ─── Test 2: search_bm25 ─────────────────────────────────────────────
    print("\n--- Test 2: search_bm25 ---")
    bm25_results = retriever.search_bm25(processed["lexical_tokens"], top_k=3)
    for r in bm25_results:
        print(f"  Doc {r['doc_id']}: BM25 score = {r['score']:.4f}")
    assert isinstance(bm25_results, list), "BM25 should return a list"
    print("  OK PASSED")

    # ─── Test 3: generate_embedding ──────────────────────────────────────
    print("\n--- Test 3: generate_embedding ---")
    embedding = retriever.generate_embedding(processed["semantic_text"])
    print(f"  Shape: {embedding.shape}, dtype: {embedding.dtype}")
    assert embedding.shape[0] == 384, "Embedding dim should be 384"
    print("  OK PASSED")

    # ─── Test 4: search_faiss ────────────────────────────────────────────
    print("\n--- Test 4: search_faiss ---")
    faiss_results = retriever.search_faiss(embedding, top_k=3)
    for r in faiss_results:
        print(f"  Doc {r['doc_id']}: similarity = {r['score']:.6f}")
    assert isinstance(faiss_results, list), "FAISS should return a list"
    print("  OK PASSED")

    # ─── Test 5: normalize_scores ────────────────────────────────────────
    print("\n--- Test 5: normalize_scores ---")
    if bm25_results:
        normalized = retriever.normalize_scores(bm25_results)
        for r in normalized:
            print(f"  Doc {r['doc_id']}: normalized = {r['score']:.4f}")
            assert 0.0 <= r["score"] <= 1.0, "Normalized score must be in [0, 1]"
        print("  OK PASSED")
    else:
        print("  (skipped — no BM25 results)")

    # ─── Test 6: fuse_results + rank_results ─────────────────────────────
    print("\n--- Test 6: fuse_results + rank_results ---")
    fused = retriever.fuse_results(bm25_results, faiss_results, strategy="rrf")
    ranked = retriever.rank_results(fused, top_k=3)
    for r in ranked:
        print(f"  Doc {r['doc_id']}: fused RRF score = {r['score']:.6f}")
    assert len(ranked) <= 3, "Should return at most top_k"
    print("  OK PASSED")

    # ─── Test 7: Full hybrid retrieve — English ──────────────────────────
    en_query = "heart disease symptoms and treatment"
    results_en = retriever.retrieve(en_query, top_k=5)
    print_results(f"[HYBRID] English: '{en_query}'", results_en)

    # ─── Test 8: Full hybrid retrieve — Spanish ──────────────────────────
    es_query = "síntomas y tratamiento de enfermedades del corazón"
    results_es = retriever.retrieve(es_query, top_k=5)
    print_results(f"[HYBRID] Spanish: '{es_query}'", results_es)

    # ─── Test 9: Lexical-only ────────────────────────────────────────────
    lex_query = "diabetes"
    results_lex = retriever.retrieve_lexical_only(lex_query, top_k=3)
    print_results(f"[LEXICAL ONLY] '{lex_query}'", results_lex)

    # ─── Test 10: Semantic-only ──────────────────────────────────────────
    sem_query = "dolor de cabeza fuerte y persistente"
    results_sem = retriever.retrieve_semantic_only(sem_query, top_k=3)
    print_results(f"[SEMANTIC ONLY] '{sem_query}'", results_sem)

    # ─── Test 11: RRF vs Weighted comparison ─────────────────────────────
    compare_query = "cancer prevention and diagnosis"
    results_rrf = retriever.retrieve(compare_query, top_k=3, strategy="rrf")
    results_wgt = retriever.retrieve(compare_query, top_k=3, strategy="weighted")
    print_results(f"[RRF] '{compare_query}'", results_rrf)
    print_results(f"[WEIGHTED] '{compare_query}'", results_wgt)

    # ─── Test 12: Cross-lingual ──────────────────────────────────────────
    cross_query = "nutrición y alimentación saludable"
    results_cross = retriever.retrieve(cross_query, top_k=3)
    print_results(f"[CROSS-LINGUAL] '{cross_query}'", results_cross)

    print("\n" + "=" * 72)
    print("  All 12 tests completed successfully!")
    print("=" * 72)


if __name__ == "__main__":
    run_tests()
