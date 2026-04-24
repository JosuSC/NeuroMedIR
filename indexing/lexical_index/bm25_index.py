from rank_bm25 import BM25Okapi
import numpy as np

class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.bm25: BM25Okapi = None
        self.doc_ids = []

    def build_index(self, tokenized_corpus: list[list[str]], doc_ids: list[int]):
        """
        Builds the BM25 inverted index from a list of tokenized documents.
        """
        if not tokenized_corpus:
            raise ValueError("Corpus is empty. Cannot build BM25 index.")
        if len(tokenized_corpus) != len(doc_ids):
            raise ValueError("Number of tokenized documents must match number of doc_ids.")

        self.doc_ids = doc_ids
        self.tokenized_corpus = tokenized_corpus
        self.bm25 = BM25Okapi(tokenized_corpus, k1=self.k1, b=self.b)

    def add_documents(self, new_token_lists: list[list[str]], new_doc_ids: list[int]):
        """Agrega nuevos documentos al índice y lo reconstruye (operación rápida)."""
        if not getattr(self, 'tokenized_corpus', None):
            self.tokenized_corpus = []
        self.tokenized_corpus.extend(new_token_lists)
        self.doc_ids.extend(new_doc_ids)
        self.bm25 = BM25Okapi(self.tokenized_corpus, k1=self.k1, b=self.b)

    def search(self, query_tokens: list[str], top_k: int = 10) -> list[dict]:
        """
        Returns top_k documents for the given lexical query.
        """
        if self.bm25 is None:
            raise RuntimeError("Index has not been built yet.")

        # Get scores for all documents
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_n = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_n:
            if scores[idx] > 0:  # Only return documents that have > 0 score
                results.append({
                    "doc_id": self.doc_ids[idx],
                    "score": float(scores[idx])
                })
        
        return results

    def get_state(self):
        """Returns the state for picking/saving."""
        return {
            "k1": self.k1,
            "b": self.b,
            "doc_ids": self.doc_ids,
            "tokenized_corpus": getattr(self, 'tokenized_corpus', []),
            "bm25": self.bm25
        }

    def load_state(self, state: dict):
        """Loads state from dictionary (used during load operation)."""
        self.k1 = state["k1"]
        self.b = state["b"]
        self.doc_ids = state["doc_ids"]
        self.tokenized_corpus = state.get("tokenized_corpus", [])
        self.bm25 = state["bm25"]
