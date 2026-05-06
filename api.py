import logging
import time
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from dynamic_expansion import expand_corpus_from_query
from retrieval.retriever import Retriever
from indexing.indexer import Indexer
from indexing.lexical_index.bm25_index import BM25Index
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.multimodal.text_encoder import TextEncoder
from retrieval.document_store import DocumentStore
from indexing.storage.index_io import IndexStorage
from indexing.configs import settings as idx_settings

from form.form_generator import extract_form_symptoms_prf, generate_dynamic_form_schema

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

class FormSubmitRequest(BaseModel):
    original_query: str
    intensity: str
    duration: str
    dynamic_symptoms: list[str] = []
    additional_notes: str = ""

@app.on_event("startup")
def startup_event():
    global retriever, indexer, doc_store
    print("Inicializando Motor BM25 + FAISS para API...")
    
    bm25 = BM25Index(k1=idx_settings.BM25_PARAMS["k1"], b=idx_settings.BM25_PARAMS["b"])
    faiss = FAISSHNSWIndex(dimension=idx_settings.EMBEDDING_DIM, m=idx_settings.HNSW_M, ef_construction=idx_settings.HNSW_EF_CONSTRUCTION)
    
    # Intentar cargar encoder; si falla (ej. sin conexión a Hugging Face), usar None
    encoder = None
    try:
        print("Cargando encoder multilíngüe...")
        encoder = TextEncoder(idx_settings.EMBEDDING_MODEL_NAME)
        print("OK: Encoder cargado correctamente.")
    except Exception as e:
        print(f"Advertencia: No se puede cargar encoder: {e}")
        print("   → Funcionando en modo BM25 (lexical-only). Búsqueda semántica deshabilitada.")
    
    doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)
    io = IndexStorage(str(idx_settings.INDEX_STORAGE_DIR))

    success = io.load_lexical(bm25) and io.load_vector(faiss)
    if not success:
        print("Advertencia: No se pudieron cargar los índices de disco.")
    
    retriever = Retriever(bm25, faiss, encoder, doc_store)
    
    indexer = Indexer()
    indexer.lexical_index = bm25
    indexer.semantic_index = faiss
    indexer.encoder = encoder
    indexer.storage = io
    
    print(f"OK: Motor listo. Documentos en memoria: {doc_store.count}")

@app.get("/api/health")
def health_check():
    # Solo responderá cuando el servidor haya terminado su bloque startup_event
    return {"status": "ready"}

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

@app.post("/api/generate_form")
def generate_form(req: QueryRequest):
    """
    Ruta para la creación dinámica del formulario dada la consulta del paciente.
    1. Recupera Top-10 artículos.
    2. Usa Pseudo-Relevance Feedback TF-IDF para aislar síntomas colaterales.
    3. Retorna un esquema JSON estructural validado para renderizar el UI.
    """
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")
        
    t_start = time.time()
    
    # 1. Buscamos inicialmente los 10 documentos más relevantes
    results = retriever.retrieve(req.query, top_k=10)
    
    # 2. Extraemos su contenido textual (se usa body y/o contexto)
    docs_text = []
    for res in results:
        content = res.get("content", "")
        title = res.get("title", "")
        # Concatenamos para mayor riqueza de palabras
        docs_text.append(f"{title} {content}")
        
    # 3. Aplicar PRF (TF-IDF Co-ocurrencias) para extraer los Top-10 síntomas/términos
    extracted_terms = extract_form_symptoms_prf(req.query, docs_text, top_n=10)
    
    # 4. Generamos el esquema estandarizado
    form_schema = generate_dynamic_form_schema(req.query, extracted_terms)
    
    return {
        "status": "success",
        "latency_ms": round((time.time() - t_start) * 1000, 1),
        "form_schema": form_schema
    }

@app.post("/api/search_with_form")
def search_with_form(req: FormSubmitRequest):
    """
    El paciente confirma y envía su formulario final rellenado.
    Construimos una mega-query más específica y precisa, y hacemos la búsqueda rígida final.
    """
    t_start = time.time()
    
    # 1. Ensamblar la Macro-Query combinando los inputs
    # Ejemplo: "tos seca (intensidad: 8) (duración: Semanas) +fiebre +asma Notas: tomo ibuprofeno"
    
    query_parts = [req.original_query]
    
    query_parts.append(f"intensidad {req.intensity}")
    query_parts.append(f"duracion {req.duration}")
    
    if req.dynamic_symptoms:
        # Penalizamos semánticamente añadiéndolos como contexto colateral esperado
        query_parts.append(" ".join(req.dynamic_symptoms))
        
    if req.additional_notes:
        query_parts.append(req.additional_notes)
        
    macro_query = " ".join(query_parts)
    print(f">> Macro-query generada desde Formulario: {macro_query}")
    
    # 2. Re-Disparo exacto del modelo con Top-K final
    results = retriever.retrieve(macro_query, top_k=10)
    
    # Formatear
    formatted_results = []
    for i, res in enumerate(results):
        formatted_results.append({
            "title": res.get("title", "Sin título"),
            "score": res.get("score", 0.0),
            "snippet": str(res.get("content", ""))[:300] + "...", 
            "url": res.get("url", "#"),
            "doc_id": res.get("doc_id", "")
        })
        
    return {
        "status": "success",
        "macro_query_used": macro_query,
        "results": formatted_results,
        "latency_ms": round((time.time() - t_start) * 1000, 1)
    }

