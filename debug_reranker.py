import json
from pathlib import Path
from indexing.lexical_index.bm25_index import BM25Index
from indexing.storage.index_io import IndexStorage
from indexing.configs import settings as idx_settings
from retrieval.document_store import DocumentStore

bm25 = BM25Index(k1=idx_settings.BM25_PARAMS["k1"], b=idx_settings.BM25_PARAMS["b"])
storage = IndexStorage(str(idx_settings.INDEX_STORAGE_DIR))
storage.load_lexical(bm25)

doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)

print(f"DocumentStore size: {doc_store.count}")

results = bm25.search(["diabetes", "sintomas"], top_k=5)
print(f"BM25 results: {results}\n")

for r in results:
    doc_id = r["doc_id"]
    doc = doc_store.get(doc_id)
    found = doc is not None
    content_len = len(doc.get("content", "")) if doc else 0
    print(f"  doc_id={repr(doc_id)}  type={type(doc_id).__name__}  found={found}  content_len={content_len}")

# Muestra algunos IDs reales del store para comparar
store_ids = list(doc_store._store.keys())[:5]
print(f"\nPrimeros 5 IDs en DocumentStore: {store_ids}")
print(f"Tipos: {[type(x).__name__ for x in store_ids]}")