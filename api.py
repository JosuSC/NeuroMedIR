"""
api.py — Endpoints FastAPI para el sistema NeuroMedIR.

Endpoints:
    GET  /api/health          — Verificación del backend
    POST /api/query           — Recuperación híbrida (BM25 + FAISS + CrossEncoder)
    POST /api/rag_query       — Pipeline RAG completo (recuperación + LLM local)
    POST /api/generate_form   — Generación dinámica de formulario PRF
    POST /api/search_with_form — Búsqueda desde formulario estructurado
"""

import logging
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from .dynamic_expansion import expand_corpus_from_query
from .retrieval.retriever import Retriever
from .retrieval.neural_reranker import NeuralReranker
from .indexing.indexer import Indexer
from .indexing.lexical_index.bm25_index import BM25Index
from .indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from .indexing.multimodal.text_encoder import TextEncoder
from .retrieval.document_store import DocumentStore
from .indexing.storage.index_io import IndexStorage
from .indexing.configs import settings as idx_settings
from .form.form_generator import extract_form_symptoms_prf, generate_dynamic_form_schema

logger = logging.getLogger(__name__)

app = FastAPI(title="NeuroMedIR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Estado global
# ---------------------------------------------------------------------------
retriever = None
indexer = None
doc_store = None
rag_pipeline = None


class QueryRequest(BaseModel):
    query: str


class RAGQueryRequest(BaseModel):
    """Modelo de petición para el pipeline RAG."""
    query: str
    top_k: Optional[int] = None


class FormSubmitRequest(BaseModel):
    original_query: str
    intensity: str
    duration: str
    dynamic_symptoms: list[str] = []
    additional_notes: str = ""


@app.on_event("startup")
def startup_event():
    """Inicializa todos los motores al arrancar."""
    global retriever, indexer, doc_store, rag_pipeline

    print("Inicializando Motor BM25 + FAISS + Cross-Encoder para API...")

    bm25 = BM25Index(k1=idx_settings.BM25_PARAMS["k1"], b=idx_settings.BM25_PARAMS["b"])
    faiss = FAISSHNSWIndex(
        dimension=idx_settings.EMBEDDING_DIM,
        m=idx_settings.HNSW_M,
        ef_construction=idx_settings.HNSW_EF_CONSTRUCTION,
    )

    encoder = None
    try:
        print("Cargando encoder multilingüe...")
        encoder = TextEncoder(idx_settings.EMBEDDING_MODEL_NAME)
        print("OK: Encoder cargado.")
    except Exception as e:
        print(f"Advertencia: No se puede cargar encoder: {e}")
        print("   → Funcionando en modo BM25 (lexical-only).")

    doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)
    io = IndexStorage(str(idx_settings.INDEX_STORAGE_DIR))

    success = io.load_lexical(bm25) and io.load_vector(faiss)
    if not success:
        print("Advertencia: No se pudieron cargar los índices de disco.")

    reranker = NeuralReranker()
    retriever = Retriever(bm25, faiss, encoder, doc_store, reranker=reranker)

    indexer = Indexer()
    indexer.lexical_index = bm25
    indexer.semantic_index = faiss
    indexer.encoder = encoder
    indexer.storage = io

    # Inicializar pipeline RAG con LLM LOCAL (sin API keys)
    # CAMBIO CLAVE: imports relativos (from .rag en vez de from rag)
    # Antes: from rag.llm_client → fallaba con "No module named 'rag'"
    # Ahora: from .rag.llm_client → funciona como parte del paquete NeuroMedIR
    try:
        from .rag.llm_client import TransformersLLMClient
        from .rag.pipeline import RAGPipeline

        llm_client = TransformersLLMClient()
        rag_pipeline = RAGPipeline(retriever=retriever, llm_client=llm_client)
        print(f"OK: RAG Pipeline configurado (LLM local: {llm_client.model_name})")
        print("   → El modelo se descargará de HuggingFace en la primera consulta.")
    except ImportError as e:
        print(f"RAG: Módulo no disponible: {e}")
    except Exception as e:
        print(f"RAG: Error de inicialización: {e}")

    print(f"OK: Motor listo. Documentos: {doc_store.count}")


@app.get("/api/health")
def health_check():
    return {"status": "ready"}


@app.post("/api/query")
def process_query(req: QueryRequest):
    """Endpoint de recuperación híbrida."""
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")

    t_start = time.time()
    results = retriever.retrieve(req.query, top_k=5)
    web_expanded = False

    if len(results) < 2 or (results and results[0].get("score", 0) < 0.3):
        print(f">> Expandiendo web: '{req.query}'")
        nuevos = expand_corpus_from_query(req.query, max_new_docs=2)
        if nuevos:
            web_expanded = True
            indexer.add_documents(nuevos)
            doc_store._load()
            results = retriever.retrieve(req.query, top_k=5)

    formatted_results = []
    for res in results:
        formatted_results.append({
            "title": res.get("title", "Sin título"),
            "score": res.get("score", 0.0),
            "snippet": str(res.get("snippet", res.get("content", "")))[:200] + "...",
            "url": res.get("url", "#"),
            "doc_id": res.get("doc_id", ""),
            "fusion_score": res.get("fusion_score"),
        })

    return {
        "results": formatted_results,
        "web_expanded": web_expanded,
        "latency_ms": round((time.time() - t_start) * 1000, 1),
    }


@app.post("/api/rag_query")
def rag_query(req: RAGQueryRequest):
    """Endpoint RAG: recuperación + generación con LLM local.

    No requiere API keys. El LLM (flan-t5-base) corre completamente local.
    """
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")

    if rag_pipeline is None or not rag_pipeline.is_available:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline no disponible. Verifique que el módulo rag/ esté instalado correctamente."
        )

    top_k = req.top_k or 5
    result = rag_pipeline.query(req.query, top_k=top_k)

    formatted_sources = []
    for src in result.get("sources", []):
        formatted_sources.append({
            "title": src.get("title", "Sin título"),
            "snippet": src.get("snippet", ""),
            "score": round(src.get("score", 0.0), 4),
            "url": src.get("url", "#"),
            "doc_id": src.get("doc_id", ""),
        })

    return {
        "answer": result["answer"],
        "sources": formatted_sources,
        "confidence": result["confidence"],
        "latency_ms": result["latency_ms"],
        "model": result["model"],
    }


@app.post("/api/generate_form")
def generate_form(req: QueryRequest):
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")

    t_start = time.time()
    results = retriever.retrieve(req.query, top_k=10)

    docs_text = []
    for res in results:
        content = res.get("content", "")
        title = res.get("title", "")
        docs_text.append(f"{title} {content}")

    extracted_terms = extract_form_symptoms_prf(req.query, docs_text, top_n=10)
    form_schema = generate_dynamic_form_schema(req.query, extracted_terms)

    return {
        "status": "success",
        "latency_ms": round((time.time() - t_start) * 1000, 1),
        "form_schema": form_schema,
    }


@app.post("/api/search_with_form")
def search_with_form(req: FormSubmitRequest):
    t_start = time.time()

    query_parts = [req.original_query]
    query_parts.append(f"intensidad {req.intensity}")
    query_parts.append(f"duracion {req.duration}")

    if req.dynamic_symptoms:
        query_parts.append(" ".join(req.dynamic_symptoms))
    if req.additional_notes:
        query_parts.append(req.additional_notes)

    macro_query = " ".join(query_parts)
    print(f">> Macro-query: {macro_query}")

    results = retriever.retrieve(macro_query, top_k=10)

    formatted_results = []
    for res in results:
        formatted_results.append({
            "title": res.get("title", "Sin título"),
            "score": res.get("score", 0.0),
            "snippet": str(res.get("snippet", res.get("content", "")))[:300] + "...",
            "url": res.get("url", "#"),
            "doc_id": res.get("doc_id", ""),
        })

    return {
        "status": "success",
        "macro_query_used": macro_query,
        "results": formatted_results,
        "latency_ms": round((time.time() - t_start) * 1000, 1),
    }