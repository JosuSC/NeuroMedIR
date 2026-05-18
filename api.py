import logging
import time
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

"""
Módulo `api.py` — Endpoints HTTP (FastAPI) para el sistema NeuroMedIR.

He documentado y comentado en un estilo cercano y humano para que sea
fácil de seguir durante la revisión de código. Aquí se exponen las rutas
principales que usa la interfaz: `health`, `query`, `generate_form` y
`search_with_form`. El backend carga los índices BM25 y FAISS en el
arranque y mantiene un `Retriever` que orquesta la búsqueda híbrida.

Notas de estilo (mías, como autor): prefiero conservar la inicialización
en `startup_event` porque simplifica los tests manuales y evita latencias
extrañas al primer request.
"""

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

# ---------------------------------------------------------------------------
# Variables globales (mantenidas simples para este proyecto académico)
# ---------------------------------------------------------------------------
# Uso variables globales para que la app se comporte igual en dev y en
# la ventana de escritorio (run_app.py). En un despliegue real cambiaría
# por un contenedor/dep inj o factory más explícita.
retriever = None
indexer = None
doc_store = None


class QueryRequest(BaseModel):
    """Modelo Pydantic para solicitudes simples de búsqueda.

    A menudo solo se envía `query` desde la UI del chat. Mantengo el
    modelo explícito para validación automática de FastAPI.
    """
    query: str


class FormSubmitRequest(BaseModel):
    """Modelo para manejar envíos de formularios dinámicos desde el UI.

    Campos:
    - `original_query`: texto original del usuario.
    - `intensity` / `duration`: campos estándar del formulario.
    - `dynamic_symptoms`: lista de síntomas seleccionados por el paciente.
    - `additional_notes`: notas libres.
    """
    original_query: str
    intensity: str
    duration: str
    dynamic_symptoms: list[str] = []
    additional_notes: str = ""


@app.on_event("startup")
def startup_event():
    """Inicialización en caliente de los motores de búsqueda.

    Aquí intento cargar BM25 y FAISS desde disco y crear el `Retriever`.
    Si no es posible cargar el encoder de embeddings, dejo el sistema
    funcionando en modo BM25 (graceful degradation).
    """
    global retriever, indexer, doc_store
    print("Inicializando Motor BM25 + FAISS para API...")
    
    # Inicializo estructuras básicas (sin realizar I/O todavía)
    bm25 = BM25Index(k1=idx_settings.BM25_PARAMS["k1"], b=idx_settings.BM25_PARAMS["b"])
    faiss = FAISSHNSWIndex(dimension=idx_settings.EMBEDDING_DIM, m=idx_settings.HNSW_M, ef_construction=idx_settings.HNSW_EF_CONSTRUCTION)
    
    # Intento crear el encoder; si falla, seguimos con BM25 solamente.
    encoder = None
    try:
        print("Cargando encoder multilíngüe...")
        encoder = TextEncoder(idx_settings.EMBEDDING_MODEL_NAME)
        print("OK: Encoder cargado correctamente.")
    except Exception as e:
        # Comento en primera persona para dejar la traza más natural.
        print(f"Advertencia: No se puede cargar encoder: {e}")
        print("   → Funcionando en modo BM25 (lexical-only). Búsqueda semántica deshabilitada.")
    
    # DocumentStore carga en memoria los JSON procesados para enriquecer resultados
    doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)
    io = IndexStorage(str(idx_settings.INDEX_STORAGE_DIR))

    # Intento cargar índices y continúo aunque fallen (notifico).
    success = io.load_lexical(bm25) and io.load_vector(faiss)
    if not success:
        print("Advertencia: No se pudieron cargar los índices de disco.")
    
    # Construyo las instancias compartidas que el API usará en runtime
    retriever = Retriever(bm25, faiss, encoder, doc_store)
    
    indexer = Indexer()
    indexer.lexical_index = bm25
    indexer.semantic_index = faiss
    indexer.encoder = encoder
    indexer.storage = io
    
    print(f"OK: Motor listo. Documentos en memoria: {doc_store.count}")


@app.get("/api/health")
def health_check():
    """Chequeo simple de salud para que la UI espere hasta que el backend esté listo."""
    return {"status": "ready"}


@app.post("/api/query")
def process_query(req: QueryRequest):
    """Endpoint principal que recibe una `query` y devuelve fuentes relevantes.

    Flujo resumido:
    1. Recuperación híbrida local con `retriever.retrieve`.
    2. Si hay pocos resultados o muy baja confianza, intento expansión web
       (llamando a `dynamic_expansion.expand_corpus_from_query`), indexo lo nuevo
       y vuelvo a recuperar.
    3. Formateo la salida para el frontend (lista de fuentes, snippet, score).

    Esta función está escrita de forma imperativa y clara para facilitar la
    lectura durante revisiones manuales.
    """
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")
        
    t_start = time.time()
    
    # 1. Búsqueda Local (BM25 + FAISS si está disponible)
    results = retriever.retrieve(req.query, top_k=5)
    
    web_expanded = False
    
    # 2. Expansión y Fallback Web: si la búsqueda local no es suficiente
    if len(results) < 2 or (results and results[0].get("score", 0) < 0.3):
        # Imprimo la acción para que el log sea fácil de seguir.
        print(f">> Consultando web para expandir: '{req.query}'")
        nuevos = expand_corpus_from_query(req.query, max_new_docs=2)
        if nuevos:
            web_expanded = True
            # Integro dinámicamente los documentos nuevos en los índices
            indexer.add_documents(nuevos)
            # Forzamos recarga del store en memoria para que los nuevos docs sean accesibles
            doc_store._load() 
            # Re-recuperar tras la expansión
            results = retriever.retrieve(req.query, top_k=5)
            
    # 3. Formatear la salida para el frontend (JSON ligero)
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
    """Genera un esquema de formulario dinámico basado en PRF desde top-k docs.

    - Extrae los top-10 artículos con el retriever.
    - Aplica `extract_form_symptoms_prf` para obtener términos relevantes.
    - Construye el `form_schema` con `generate_dynamic_form_schema`.

    El objetivo es ofrecer al frontend un JSON que represente preguntas
    médicas útiles para refinar la búsqueda.
    """
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")
        
    t_start = time.time()
    
    # 1. Recupero top documentos
    results = retriever.retrieve(req.query, top_k=10)
    
    # 2. Concateno texto para análisis PRF
    docs_text = []
    for res in results:
        content = res.get("content", "")
        title = res.get("title", "")
        docs_text.append(f"{title} {content}")
        
    # 3. Extraigo términos por PRF
    extracted_terms = extract_form_symptoms_prf(req.query, docs_text, top_n=10)
    
    # 4. Genero esquema y lo devuelvo
    form_schema = generate_dynamic_form_schema(req.query, extracted_terms)
    
    return {
        "status": "success",
        "latency_ms": round((time.time() - t_start) * 1000, 1),
        "form_schema": form_schema
    }


@app.post("/api/search_with_form")
def search_with_form(req: FormSubmitRequest):
    """Recibe el formulario completo, compone una macro-query y busca de nuevo.

    Esto permite transformar inputs estructurados (intensidad, duración,
    síntomas seleccionados) en una consulta más precisa para el motor de SRI.
    """
    t_start = time.time()
    
    # 1. Ensamblar la Macro-Query combinando los inputs
    query_parts = [req.original_query]
    query_parts.append(f"intensidad {req.intensity}")
    query_parts.append(f"duracion {req.duration}")
    
    if req.dynamic_symptoms:
        query_parts.append(" ".join(req.dynamic_symptoms))
        
    if req.additional_notes:
        query_parts.append(req.additional_notes)
        
    macro_query = " ".join(query_parts)
    print(f">> Macro-query generada desde Formulario: {macro_query}")
    
    # 2. Re-Disparo exacto del motor con la macro-query
    results = retriever.retrieve(macro_query, top_k=10)
    
    # 3. Formatear la respuesta
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

