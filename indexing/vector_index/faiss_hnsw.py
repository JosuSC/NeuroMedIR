import faiss
import numpy as np

class FAISSHNSWIndex:
    def __init__(self, dimension: int, m: int = 32, ef_construction: int = 40):
        self.dimension = dimension
        self.m = m
        self.ef_construction = ef_construction
        self.index = None
        self.doc_ids = []
        self.doc_texts = {}

    @staticmethod
    def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
        """L2-normalize vectors row-wise to approximate cosine with L2 search."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)  # Avoid division by zero.
        return vectors / norms

    def build_index(self, embeddings: np.ndarray, doc_ids: list[int]):
        """
        Builds the HNSW vector index using FAISS.
        """
        if embeddings is None or len(embeddings) == 0:
            raise ValueError("Embeddings are empty. Cannot build FAISS index.")
            
        embeddings = np.array(embeddings).astype('float32') # FAISS requires float32
        
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embeddings dimension {embeddings.shape[1]} does not match initialized dimension {self.dimension}.")
        if embeddings.shape[0] != len(doc_ids):
            raise ValueError("Number of embeddings must match number of doc_ids.")

        # Normalize document vectors so L2 distance becomes a proxy for cosine similarity.
        embeddings = self._l2_normalize(embeddings)

        # HNSW with L2 metric.
        self.index = faiss.IndexHNSWFlat(self.dimension, self.m)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Add vectors
        self.index.add(embeddings)
        self.doc_ids = doc_ids

    def add_embeddings(self, new_embeddings: np.ndarray, new_doc_ids: list[int]):
        """Increments the FAISS index with new embeddings."""
        if self.index is None:
            self.build_index(new_embeddings, new_doc_ids)
            return

        new_embeddings = np.array(new_embeddings).astype('float32')
        if new_embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embeddings dimension mismatch.")
        if new_embeddings.shape[0] != len(new_doc_ids):
            raise ValueError("Number of embeddings must match number of doc_ids.")

        new_embeddings = self._l2_normalize(new_embeddings)
        self.index.add(new_embeddings)
        self.doc_ids.extend(new_doc_ids)

    def search(self, query_embedding: np.ndarray, top_k: int = 10, ef_search: int = 16) -> list[dict]:
        """
        Searches for the nearest neighbors of the query embedding using HNSW graph.
        """
        if self.index is None:
            raise RuntimeError("FAISS Index has not been built yet.")

        # Ensure query is float32 and shape is (1, d)
        query_embedding = np.array(query_embedding).astype('float32')
        if len(query_embedding.shape) == 1:
            query_embedding = np.expand_dims(query_embedding, axis=0)

        # Normalize query vector with same policy used at indexing time.
        query_embedding = self._l2_normalize(query_embedding)

        # Set search ef
        self.index.hnsw.efSearch = ef_search
        
        # Search returns squared L2 distances and indices
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for i in range(top_k):
            idx = indices[0][i]
            if idx != -1:  # FAISS returns -1 if there are not enough items
                # For L2 distance, smaller is better. We might invert it or return distance
                results.append({
                    "doc_id": self.doc_ids[idx],
                    "l2_distance": float(distances[0][i])
                })
                
        return results

    def save_to_disk(self, filepath: str):
        if self.index is None:
            raise RuntimeError("Cannot save an empty index.")
        faiss.write_index(self.index, filepath)

    def load_from_disk(self, filepath: str, doc_ids: list[int]):
        self.index = faiss.read_index(filepath)
        self.doc_ids = doc_ids

    def set_text_mapping(self, doc_texts: dict[int, str]):
        """Attach a document text mapping for future RAG/enrichment usage."""
        self.doc_texts = doc_texts or {}
