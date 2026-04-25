import logging
import time
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dynamic_expansion import expand_corpus_from_query
from retrieval.retriever import Retriever
from indexing.indexer import Indexer
from indexing.lexical_index.bm25_index import BM25Index
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.multimodal.text_encoder import TextEncoder
from retrieval.document_store import DocumentStore
from indexing.storage.index_io import IndexStorage
from indexing.configs import settings as idx_settings

app = FastAPI(title="NeuroMedIR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales para los motores
retriever = None
indexer = None
doc_store = None

class QueryRequest(BaseModel):
    query: str

@app.on_event("startup")
def startup_event():
    global retriever, indexer, doc_store
    print("Inicializando Motor BM25 + FAISS para API...")
    
    bm25 = BM25Index(k1=idx_settings.BM25_PARAMS["k1"], b=idx_settings.BM25_PARAMS["b"])
    faiss = FAISSHNSWIndex(dimension=idx_settings.EMBEDDING_DIM, m=idx_settings.HNSW_M, ef_construction=idx_settings.HNSW_EF_CONSTRUCTION)
    encoder = TextEncoder(idx_settings.EMBEDDING_MODEL_NAME)
    doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)
    io = IndexStorage(str(idx_settings.INDEX_STORAGE_DIR))

    success = io.load_lexical(bm25) and io.load_vector(faiss)
    if not success:
        print("⚠️ Advertencia: No se pudieron cargar los índices de disco.")
    
    retriever = Retriever(bm25, faiss, encoder, doc_store)
    
    indexer = Indexer()
    indexer.lexical_index = bm25
    indexer.semantic_index = faiss
    indexer.encoder = encoder
    indexer.storage = io
    
    print(f"✔ Motor listo. Documentos en memoria: {doc_store.count}")

@app.post("/api/query")
def process_query(req: QueryRequest):
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")
        
    t_start = time.time()
    
    # 1. Búsqueda Local (RAG)
    results = retriever.retrieve(req.query, top_k=5)
    
    web_expanded = False
    
    # 2. Expansión y Fallback Web
    if len(results) < 2 or (results and results[0].get("score", 0) < 0.3):
        # Simulamos que no hubo buena info local, vamos a la web
        print(f">> Consultando web para expandir: '{req.query}'")
        nuevos = expand_corpus_from_query(req.query, max_new_docs=2)
        if nuevos:
            web_expanded = True
            indexer.add_documents(nuevos)
            doc_store._load() 
            # Re-recuperar
            results = retriever.retrieve(req.query, top_k=5)
            
    # Formatear la salida para el frontend
    formatted_results = []
    for i, res in enumerate(results):
        formatted_results.append({
            "title": res.get("title", "Sin título"),
            "score": res.get("score", 0.0),
            "snippet": str(res.get("content", ""))[:200] + "...", 
            "url": res.get("url", "#"),
            "doc_id": res.get("doc_id", "")
        })
        
    return {
        "results": formatted_results,
        "web_expanded": web_expanded,
        "latency_ms": round((time.time() - t_start) * 1000, 1)
    }
