import pickle
import os
from pathlib import Path

class IndexStorage:
    """
    Handles saving and loading the complex multimodule states for the lexical
    and vector indices, alongside their metadata.
    """
    
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.bm25_state_path = self.storage_dir / "bm25_lexical.pkl"
        self.faiss_index_path = self.storage_dir / "faiss_semantic.index"
        self.faiss_metadata_path = self.storage_dir / "faiss_metadata.pkl"

    def save_lexical(self, lexical_index):
        """Saves BM25 index and ID metadata via pickle."""
        state = lexical_index.get_state()
        with open(self.bm25_state_path, "wb") as f:
            pickle.dump(state, f)

    def load_lexical(self, lexical_index) -> bool:
        """Loads BM25 index state."""
        if not self.bm25_state_path.exists():
            return False
            
        with open(self.bm25_state_path, "rb") as f:
            state = pickle.load(f)
        lexical_index.load_state(state)
        return True

    def save_vector(self, vector_index, doc_texts: dict[int, str] = None):
        """Saves FAISS index and metadata (Doc IDs + optional doc text mapping)."""
        vector_index.save_to_disk(str(self.faiss_index_path))
        
        with open(self.faiss_metadata_path, "wb") as f:
            pickle.dump(
                {
                    "doc_ids": vector_index.doc_ids,
                    "doc_texts": doc_texts or {},
                },
                f,
            )

    def load_vector(self, vector_index) -> bool:
        """Loads FAISS index and doc IDs."""
        if not self.faiss_index_path.exists() or not self.faiss_metadata_path.exists():
            return False
            
        with open(self.faiss_metadata_path, "rb") as f:
            meta = pickle.load(f)
            
        vector_index.load_from_disk(str(self.faiss_index_path), meta["doc_ids"])
        vector_index.set_text_mapping(meta.get("doc_texts", {}))
        return True
