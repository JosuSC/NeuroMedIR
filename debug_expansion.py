"""
debug_expansion.py — Verifica el estado del expansion_retriever y su doc_store.
Ejecutar desde la raíz: python debug_expansion.py
"""
import logging
logging.basicConfig(level=logging.INFO)

from indexing.configs import settings as idx_settings
from retrieval.document_store import DocumentStore

print("\n=== Rutas de expansión ===")
print(f"EXPANSION_DATA_DIR: {idx_settings.EXPANSION_DATA_DIR}")
print(f"EXPANSION_INDEX_DIR: {idx_settings.EXPANSION_INDEX_DIR}")
print(f"  data dir existe: {idx_settings.EXPANSION_DATA_DIR.exists()}")
print(f"  index dir existe: {idx_settings.EXPANSION_INDEX_DIR.exists()}")

# ¿Cuántos docs hay en el store de expansión?
exp_store = DocumentStore(idx_settings.EXPANSION_DATA_DIR)
print(f"\nExpansion DocumentStore size: {exp_store.count}")

# ¿Los índices de expansión cargan?
from indexing.lexical_index.bm25_index import BM25Index
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.storage.index_io import IndexStorage

exp_bm25 = BM25Index(k1=idx_settings.BM25_PARAMS["k1"], b=idx_settings.BM25_PARAMS["b"])
exp_faiss = FAISSHNSWIndex(
    dimension=idx_settings.EMBEDDING_DIM,
    m=idx_settings.HNSW_M,
    ef_construction=idx_settings.HNSW_EF_CONSTRUCTION,
)
exp_storage = IndexStorage(str(idx_settings.EXPANSION_INDEX_DIR))
lex_ok = exp_storage.load_lexical(exp_bm25)
vec_ok = exp_storage.load_vector(exp_faiss)
print(f"\nExpansion lexical index carga: {lex_ok}")
print(f"Expansion vector index carga: {vec_ok}")
print(f"\n=> Si el store de expansión tiene docs pero el índice apunta a IDs")
print(f"   que no están en ese store, el reranker recibe doc_texts vacíos.")