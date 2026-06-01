"""
debug_pipeline.py — Diagnostica qué llega al NeuralReranker durante retrieve()
Ejecutar desde la raíz de NeuroMedIR: python debug_pipeline.py
"""
import logging
logging.basicConfig(level=logging.INFO)

from indexing.lexical_index.bm25_index import BM25Index
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.multimodal.text_encoder import TextEncoder
from indexing.storage.index_io import IndexStorage
from indexing.configs import settings as idx_settings
from retrieval.document_store import DocumentStore
from retrieval.neural_reranker import NeuralReranker
from retrieval.configs import settings as ret_settings

# ── Cargar componentes ──────────────────────────────────────────────────────
print("\n=== Cargando componentes ===")
bm25 = BM25Index(k1=idx_settings.BM25_PARAMS["k1"], b=idx_settings.BM25_PARAMS["b"])
faiss = FAISSHNSWIndex(
    dimension=idx_settings.EMBEDDING_DIM,
    m=idx_settings.HNSW_M,
    ef_construction=idx_settings.HNSW_EF_CONSTRUCTION,
)
encoder = TextEncoder(idx_settings.EMBEDDING_MODEL_NAME)
doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)
storage = IndexStorage(str(idx_settings.INDEX_STORAGE_DIR))
storage.load_lexical(bm25)
storage.load_vector(faiss)

reranker = NeuralReranker()
print(f"Reranker is_enabled: {reranker.is_enabled}")
print(f"Reranker model_name: {reranker.model_name}")

# ── Simular Stage 1 ─────────────────────────────────────────────────────────
print("\n=== Stage 1: BM25 + FAISS ===")
query = "síntomas de diabetes tipo 2"

from retrieval.query_processor import QueryProcessor
from indexing.preprocess.text_cleaner import TextCleaner
from retrieval.semantic_search import SemanticSearch
from retrieval.fusion import fuse_results, rank_results

cleaner = TextCleaner()
qp = QueryProcessor(cleaner=cleaner)
processed = qp.process(query)
print(f"Tokens: {processed['lexical_tokens']}")

lex = bm25.search(processed["lexical_tokens"], top_k=ret_settings.LEXICAL_TOP_K)
print(f"BM25 hits: {len(lex)}")

ss = SemanticSearch(encoder=encoder, vector_index=faiss)
emb = ss.generate_embedding(processed["semantic_text"])
sem = ss.search_faiss(emb, top_k=ret_settings.SEMANTIC_TOP_K)
print(f"FAISS hits: {len(sem)}")

fused = fuse_results(lex, sem)
ranked = rank_results(fused, top_k=ret_settings.RERANK_TOP_K)
print(f"Fused+ranked candidates para rerank: {len(ranked)}")

# ── Simular lo que hace el Retriever antes de llamar al reranker ─────────────
print("\n=== Verificando doc_texts que llegan al reranker ===")
doc_ids = [r["doc_id"] for r in ranked]
doc_texts = doc_store.get_texts(doc_ids)

print(f"doc_ids count: {len(doc_ids)}")
print(f"doc_texts count: {len(doc_texts)}")
print(f"doc_texts vacíos: {sum(1 for v in doc_texts.values() if not v)}")
print(f"Primeros 3 doc_ids: {doc_ids[:3]}")
for did in doc_ids[:3]:
    txt = doc_texts.get(did, "NOT FOUND")
    print(f"  doc_id={did}: {len(txt) if isinstance(txt, str) else 'NOT FOUND'} chars")

# ── Llamar al reranker directamente ─────────────────────────────────────────
print("\n=== Llamando reranker.rerank() directamente ===")
reranked = reranker.rerank(query, ranked, doc_texts, top_k=5)
print(f"Reranked results: {len(reranked)}")
for r in reranked[:3]:
    print(f"  {r}")