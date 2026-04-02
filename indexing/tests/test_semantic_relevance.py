import unittest
from unittest.mock import patch

import numpy as np

from indexing.indexer import Indexer


class FakeTextEncoder:
    """Deterministic encoder for semantic relevance tests."""

    def __init__(self, model_name: str, batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = batch_size

    def encode(self, inputs):
        if isinstance(inputs, str):
            inputs = [inputs]

        vectors = []
        for text in inputs:
            t = text.lower()
            v = np.zeros(384, dtype=np.float32)

            if any(k in t for k in ["heart", "cardiac", "attack", "chest pain"]):
                v[0] = 1.0
            if any(k in t for k in ["migraine", "headache", "head pain"]):
                v[1] = 1.0
            if any(k in t for k in ["diabetes", "insulin", "glucose"]):
                v[2] = 1.0

            # Fallback concept to avoid zero vectors.
            if not v.any():
                v[3] = 1.0

            vectors.append(v)

        return np.vstack(vectors)


class TestIndexerSemanticRelevance(unittest.TestCase):
    @patch("indexing.indexer.TextEncoder", FakeTextEncoder)
    def test_search_semantic_relevance(self):
        """search_semantic should rank the semantically closest document first."""
        indexer = Indexer()

        docs = [
            {
                "id": 1,
                "title": "Heart attack warning signs",
                "content": "Common heart attack symptoms include chest pain and shortness of breath.",
            },
            {
                "id": 2,
                "title": "Migraine management",
                "content": "Migraine and headache treatment options include rest and hydration.",
            },
            {
                "id": 3,
                "title": "Diabetes care",
                "content": "Diabetes control may require insulin and glucose monitoring.",
            },
        ]

        indexer.index_documents(docs)

        query = "cardiac attack symptoms"
        results = indexer.search_semantic(query, top_k=3)

        self.assertTrue(results, "Semantic search returned no results")
        self.assertEqual(results[0]["doc_id"], 1, "Top semantic result should match cardiac concept")

        retrieved_ids = [r["doc_id"] for r in results]
        self.assertIn(1, retrieved_ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
