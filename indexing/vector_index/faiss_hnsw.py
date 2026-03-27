import faiss
import numpy as np

class FAISSHNSWIndex:
    def __init__(self, dimension: int, m: int = 32, ef_construction: int = 40):
        self.dimension = dimension
        self.m = m
        self.ef_construction = ef_construction
        self.index = None
        self.doc_ids = []

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

        # L2 distance is typically used, but inner product (cosine similarity) can be used 
        # if vectors are normalized. SentenceTransformers normally outputs unnormalized 
        # vectors unless specified, but HNSW in FAISS usually operates on L2.
        self.index = faiss.IndexHNSWFlat(self.dimension, self.m)
        self.index.hnsw.efConstruction = self.ef_construction
        
        # Add vectors
        self.index.add(embeddings)
        self.doc_ids = doc_ids

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
