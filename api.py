"""
api.py — FastAPI endpoints para el sistema NeuroMedIR.

Endpoints:
    GET  /api/health              — Health check del backend
    POST /api/chat                — Endpoint conversacional unificado
    POST /api/chat/submit_form   — Envío de formulario de síntomas
    POST /api/query              — Retrieval híbrido directo (legacy)
    POST /api/rag_query          — Pipeline RAG directo (legacy)

Flujo conversacional:
    Mensaje del usuario → IntentClassifier → Saludo/Pregunta/Síntomas
        - SALUDO:     Respuesta amigable conversacional
        - PREGUNTA:   RAG → Respuesta conversacional + Bibliografía
        - SÍNTOMAS:   Formulario dinámico → [usuario rellena] → Diagnóstico + Bibliografía
        - DESPEDIDA:  Respuesta de despedida con disclaimer
"""

import random
import logging
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path

from retrieval.retriever import Retriever
from retrieval.neural_reranker import NeuralReranker
from indexing.indexer import Indexer
from indexing.lexical_index.bm25_index import BM25Index
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.multimodal.text_encoder import TextEncoder
from retrieval.document_store import DocumentStore
from indexing.storage.index_io import IndexStorage
from indexing.configs import settings as idx_settings
from chat.intent_classifier import IntentClassifier, IntentType
from chat.diagnosis_engine import DiagnosisEngine
from chat.configs import settings as chat_settings
from form.form_generator import extract_form_symptoms_prf, generate_dynamic_form_schema
from dynamic_expansion import expand_corpus_from_query

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
# Estado global del sistema
# ---------------------------------------------------------------------------
retriever: Optional[Retriever] = None
indexer: Optional[Indexer] = None
doc_store: Optional[DocumentStore] = None
rag_pipeline = None
intent_classifier: Optional[IntentClassifier] = None
diagnosis_engine: Optional[DiagnosisEngine] = None

# ---------------------------------------------------------------------------
# Configuracion de expansion web automatica
# ---------------------------------------------------------------------------
MIN_RESULTS_FOR_ANSWER = 3
WEB_EXPANSION_TARGET_DOCS = 5


# ---------------------------------------------------------------------------
# Modelos de request
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Request para el endpoint conversacional unificado."""
    message: str
    lang: Optional[str] = None


class FormSubmitRequest(BaseModel):
    """Request para envío de formulario de síntomas."""
    original_query: str
    intensity: str = "5"
    duration: str = ""
    dynamic_symptoms: List[str] = []
    additional_notes: str = ""
    extra_fields: List[str] = []
    lang: Optional[str] = None


class QueryRequest(BaseModel):
    """Request para retrieval directo (legacy)."""
    query: str


class RAGQueryRequest(BaseModel):
    """Request para RAG directo (legacy)."""
    query: str
    top_k: Optional[int] = None


# ---------------------------------------------------------------------------
# Startup: Inicializar todos los motores
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    """Inicializa todos los motores del sistema al arrancar."""
    global retriever, indexer, doc_store, rag_pipeline
    global intent_classifier, diagnosis_engine

    print("Inicializando Motor BM25 + FAISS + Cross-Encoder para API...")

    # --- Motor de Retrieval Híbrido ---
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
    if encoder is not None:
        indexer.encoder = encoder
    indexer.storage = io

    # --- Pipeline RAG (LLM local) ---
    try:
        from rag.llm_client import GeminiLLMClient, OpenRouterLLMClient, FallbackLLMClient
        from rag.pipeline import RAGPipeline

        llm_client = FallbackLLMClient([
            GeminiLLMClient(),
            OpenRouterLLMClient(),
        ])
        rag_pipeline = RAGPipeline(retriever=retriever, llm_client=llm_client)
        if llm_client.is_available:
            print(f"OK: RAG Pipeline configurado ({llm_client.model_name})")
        else:
            print("Advertencia: no hay LLM configurado. RAG quedará deshabilitado hasta definirlo.")
    except ImportError as e:
        print(f"RAG: Módulo no disponible: {e}")
        rag_pipeline = None
    except Exception as e:
        print(f"RAG: Error de inicialización: {e}")
        rag_pipeline = None

    # --- Clasificador de Intención ---
    intent_classifier = IntentClassifier()
    print("OK: Clasificador de intención inicializado.")

    # --- Motor de Diagnóstico ---
    diagnosis_engine = DiagnosisEngine()
    print("OK: Motor de diagnóstico inicializado.")

    print(f"OK: Sistema listo. Documentos: {doc_store.count}")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """Verifica que el backend esté listo."""
    return {"status": "ready"}


# ---------------------------------------------------------------------------
# ENDPOINT PRINCIPAL: Chat conversacional unificado
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """
    Endpoint conversacional unificado.

    Clasifica la intención del usuario y responde según el flujo:
        - SALUDO:     Respuesta amigable
        - PREGUNTA:   RAG → respuesta conversacional + bibliografía
        - SÍNTOMAS:   Genera formulario dinámico para que el paciente rellene
        - DESPEDIDA:  Respuesta de despedida + disclaimer médico

    Returns:
        {
            "type": "greeting" | "question" | "symptoms" | "farewell",
            "message": str,           # Respuesta conversacional
            "form_schema": dict|null, # Solo si type=symptoms
            "diagnoses": list|null,   # Solo si type=question con RAG
            "bibliography": list|null,# Referencias usadas
        }
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    # Clasificar la intención del mensaje
    classification = intent_classifier.classify(req.message)
    intent = classification["intent"]
    detected_symptoms = classification.get("detected_symptoms", [])

    # Detectar idioma (o respetar selección de UI si viene definida)
    requested_lang = req.lang if req.lang in {"es", "en"} else None
    is_spanish = True if requested_lang == "es" else False if requested_lang == "en" else _detect_spanish(req.message)
    lang_code = "es" if is_spanish else "en"

    # ============================================================
    # SALUDO → Respuesta amigable conversacional
    # ============================================================
    if intent == IntentType.SALUDO:
        greetings = chat_settings.SALUDOS_ES if is_spanish else chat_settings.SALUDOS_EN
        message = random.choice(greetings)

        return {
            "type": "greeting",
            "message": message,
            "form_schema": None,
            "diagnoses": None,
            "bibliography": None,
        }

    # ============================================================
    # DESPEDIDA → Respuesta de despedida + disclaimer
    # ============================================================
    if intent == IntentType.DESPEDIDA:
        farewells = chat_settings.DESPEDIDAS_ES if is_spanish else chat_settings.DESPEDIDAS_EN
        message = random.choice(farewells)

        return {
            "type": "farewell",
            "message": message,
            "form_schema": None,
            "diagnoses": None,
            "bibliography": None,
        }

    # ============================================================
    # SÍNTOMAS → Generar formulario dinámico
    # ============================================================
    if intent == IntentType.SINTOMAS:
        return _handle_symptoms(req.message, detected_symptoms, lang_code)

    # ============================================================
    # PREGUNTA → RAG conversacional + bibliografía
    # ============================================================
    if intent == IntentType.PREGUNTA:
        return _handle_question(req.message, lang_code)

    # Fallback
    return {
        "type": "greeting",
        "message": "¿En qué puedo ayudarte? Puedes preguntarme sobre temas médicos o contarme tus síntomas.",
        "form_schema": None,
        "diagnoses": None,
        "bibliography": None,
    }


def _handle_symptoms(message: str, detected_symptoms: list, lang_code: str) -> dict:
    """
    Maneja mensajes con síntomas: genera formulario dinámico.
    Usa PRF (Pseudo-Relevance Feedback) para extraer términos médicos
    adicionales de los documentos recuperados y enriquecer el formulario.
    """
    t_start = time.time()

    # Recuperar documentos para PRF
    results = retriever.retrieve(message, top_k=10)

    if _should_expand(results):
        used_web_search = _try_expand_corpus(message)
        if used_web_search:
            results = retriever.retrieve(message, top_k=10)

    # Extraer términos médicos adicionales de los documentos
    docs_text = []
    for res in results:
        content = res.get("content", "")
        title = res.get("title", "")
        docs_text.append(f"{title} {content}")

    extracted_terms = extract_form_symptoms_prf(message, docs_text, top_n=10)

    # Combinar síntomas detectados del mensaje con los extraídos por PRF
    combined_symptoms = list(detected_symptoms)
    for term in extracted_terms:
        term_lower = term.lower()
        if not any(term_lower in s.lower() for s in combined_symptoms):
            combined_symptoms.append(term)

    # Generar esquema del formulario dinámico
    form_schema = generate_dynamic_form_schema(
        message,
        combined_symptoms,
        detected_symptoms=detected_symptoms,
        lang=lang_code,
    )

    # Agregar síntomas detectados del mensaje al esquema
    if detected_symptoms:
        form_schema["detected_symptoms"] = detected_symptoms

    latency_ms = round((time.time() - t_start) * 1000, 1)
    logger.info(f"Formulario generado en {latency_ms}ms para: '{message[:50]}...'")

    if lang_code == "es":
        intro_msg = (
            "Entiendo que tienes algunos síntomas. Para poder ayudarte mejor, "
            "por favor completa el siguiente formulario con más detalles sobre tu caso. "
            "Esto me permitirá darte una respuesta más precisa."
        )
    else:
        intro_msg = (
            "I understand you're experiencing some symptoms. To help you better, "
            "please fill out the following form with more details about your case. "
            "This will allow me to give you a more precise response."
        )

    return {
        "type": "symptoms",
        "message": intro_msg,
        "form_schema": form_schema,
        "diagnoses": None,
        "bibliography": None,
    }


def _handle_question(message: str, lang_code: str) -> dict:
    """
    Maneja preguntas generales: RAG → respuesta conversacional + bibliografía.
    """
    t_start = time.time()

    # Evaluar si la base local es insuficiente y activar expansion web
    used_web_search = False
    try:
        initial_results = retriever.retrieve(message, top_k=5)
    except Exception as e:
        logger.error(f"Retrieval inicial fallo: {e}")
        initial_results = []

    if _should_expand(initial_results):
        used_web_search = _try_expand_corpus(message)
        if used_web_search:
            logger.info("Expansion web activa: reintentando retrieval tras indexacion dinamica.")

    # Intentar RAG primero (genera respuesta natural)
    answer_text = None
    sources = []
    confidence = 0.0

    if rag_pipeline is not None and rag_pipeline.is_available:
        try:
            rag_result = rag_pipeline.query(message, top_k=5, lang=lang_code)
            answer_text = rag_result.get("answer")
            sources = rag_result.get("sources", [])
            confidence = rag_result.get("confidence", 0.0)
        except Exception as e:
            logger.error(f"RAG falló para pregunta: {e}")
            answer_text = None

    # Si la respuesta indica insuficiencia, intentar expansión web y reintentar
    if answer_text and _answer_indicates_insufficient(answer_text):
        if not used_web_search:
            used_web_search = _try_expand_corpus(message)
        if used_web_search and rag_pipeline is not None and rag_pipeline.is_available:
            try:
                rag_result = rag_pipeline.query(message, top_k=5, lang=lang_code)
                answer_text = rag_result.get("answer")
                sources = rag_result.get("sources", [])
                confidence = rag_result.get("confidence", 0.0)
            except Exception as e:
                logger.error(f"RAG falló tras expansión web: {e}")

    # Si hay baja confianza, intentar expansión web una vez
    if answer_text and confidence < 0.15 and not used_web_search:
        used_web_search = _try_expand_corpus(message)
        if used_web_search and rag_pipeline is not None and rag_pipeline.is_available:
            try:
                rag_result = rag_pipeline.query(message, top_k=5, lang=lang_code)
                answer_text = rag_result.get("answer")
                sources = rag_result.get("sources", [])
                confidence = rag_result.get("confidence", 0.0)
            except Exception as e:
                logger.error(f"RAG falló tras expansión web por baja confianza: {e}")

    # Si RAG no está disponible o falló, usar retrieval directo
    if answer_text is None:
        results = retriever.retrieve(message, top_k=5)
        sources = results
        if lang_code == "es":
            answer_text = _build_answer_from_results(results, "es")
        else:
            answer_text = _build_answer_from_results(results, "en")

    # Construir bibliografía
    bibliography = diagnosis_engine._build_bibliography(sources) if sources else []

    # Agregar disclaimer
    disclaimer = chat_settings.DISCLAIMER_ES if lang_code == "es" else chat_settings.DISCLAIMER_EN

    latency_ms = round((time.time() - t_start) * 1000, 1)
    logger.info(f"Pregunta respondida en {latency_ms}ms (RAG={'sí' if rag_pipeline else 'no'})")

    return {
        "type": "question",
        "message": answer_text,
        "form_schema": None,
        "diagnoses": None,
        "bibliography": bibliography,
        "disclaimer": disclaimer,
        "used_web_search": used_web_search,
    }


# ---------------------------------------------------------------------------
# ENDPOINT: Envío de formulario de síntomas
# ---------------------------------------------------------------------------

@app.post("/api/chat/submit_form")
def submit_form(req: FormSubmitRequest):
    """
    Procesa el formulario rellenado por el paciente y genera diagnóstico.

    Flujo:
        1. Construir macro-query con síntomas originales + formulario
        2. Recuperar documentos con el motor híbrido
        3. Generar diagnósticos diferenciales con probabilidades
        4. Intentar generar respuesta conversacional con RAG
        5. Adjuntar bibliografía

    Returns:
        {
            "type": "diagnosis",
            "message": str,           # Respuesta conversacional del asistente
            "diagnoses": list,        # Diagnósticos con probabilidades
            "bibliography": list,     # Referencias usadas
            "disclaimer": str,        # Aviso médico
        }
    """
    t_start = time.time()

    # Paso 1: Construir macro-query enriquecida
    query_parts = [req.original_query]

    if req.intensity:
        query_parts.append(f"intensidad {req.intensity}")
    if req.duration:
        query_parts.append(f"duracion {req.duration}")
    if req.dynamic_symptoms:
        query_parts.append(" ".join(req.dynamic_symptoms))
    if req.extra_fields:
        query_parts.append(" ".join(req.extra_fields))
    if req.additional_notes:
        query_parts.append(req.additional_notes)

    macro_query = " ".join(query_parts)
    logger.info(f"Macro-query para diagnóstico: {macro_query}")

    # Paso 2: Recuperar documentos
    results = retriever.retrieve(macro_query, top_k=chat_settings.DIAGNOSIS_TOP_K)
    if _should_expand(results):
        used_web_search = _try_expand_corpus(macro_query)
        if used_web_search:
            results = retriever.retrieve(macro_query, top_k=chat_settings.DIAGNOSIS_TOP_K)

    # Paso 3: Generar diagnósticos
    requested_lang = req.lang if req.lang in {"es", "en"} else None
    lang_code = "es" if requested_lang == "es" else "en" if requested_lang == "en" else None
    lang_final = lang_code or ("es" if _detect_spanish(req.original_query) else "en")
    diagnosis_result = diagnosis_engine.generate_diagnosis(macro_query, results, lang=lang_final)
    diagnoses = diagnosis_result.get("diagnoses", [])
    bibliography = diagnosis_result.get("bibliography", [])
    summary = diagnosis_result.get("summary", "")

    # Paso 4: Intentar RAG para respuesta conversacional más natural
    answer_text = None
    if rag_pipeline is not None and rag_pipeline.is_available:
        try:
            diag_prompt = (
                f"Diagnóstico diferencial para: {macro_query}"
                if lang_final == "es"
                else f"Differential diagnosis for: {macro_query}"
            )
            rag_result = rag_pipeline.query(
                diag_prompt,
                top_k=chat_settings.DIAGNOSIS_TOP_K,
                lang=lang_final,
            )
            answer_text = rag_result.get("answer")
        except Exception as e:
            logger.error(f"RAG falló para diagnóstico: {e}")

    # Si RAG no está disponible, usar el summary del DiagnosisEngine
    if answer_text is None:
        answer_text = summary
    elif summary:
        if lang_final == "es":
            answer_text = f"{answer_text}\n\nResumen del análisis:\n{summary}"
        else:
            answer_text = f"{answer_text}\n\nAnalysis summary:\n{summary}"

    # Detectar idioma
    is_spanish = True if (lang_final == "es") else False if (lang_final == "en") else _detect_spanish(req.original_query)
    disclaimer = chat_settings.DISCLAIMER_ES if is_spanish else chat_settings.DISCLAIMER_EN

    latency_ms = round((time.time() - t_start) * 1000, 1)
    logger.info(
        f"Diagnóstico completado en {latency_ms}ms — "
        f"{len(diagnoses)} condiciones, {len(bibliography)} referencias"
    )

    return {
        "type": "diagnosis",
        "message": answer_text,
        "diagnoses": diagnoses,
        "bibliography": bibliography,
        "disclaimer": disclaimer,
    }


# ---------------------------------------------------------------------------
# Legacy endpoints (mantenidos por compatibilidad)
# ---------------------------------------------------------------------------

@app.post("/api/query")
def process_query(req: QueryRequest):
    """Retrieval híbrido directo (legacy — sin clasificación de intención)."""
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")

    t_start = time.time()
    results = retriever.retrieve(req.query, top_k=5)
    used_web_search = False
    if _should_expand(results):
        used_web_search = _try_expand_corpus(req.query)
        if used_web_search:
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
            "source": res.get("source", ""),
            "category": res.get("category", "other"),
        })

    return {
        "results": formatted_results,
        "latency_ms": round((time.time() - t_start) * 1000, 1),
        "used_web_search": used_web_search,
    }


def _should_expand(results: list) -> bool:
    """Retorna True si la base local es insuficiente para responder."""
    if results is None:
        return True
    if len(results) < MIN_RESULTS_FOR_ANSWER:
        return True
    top_score = results[0].get("score", 0.0) if results else 0.0
    return top_score < 0.15


def _try_expand_corpus(query: str) -> bool:
    """Ejecuta expansion web y reindexa incrementalmente si es posible."""
    global doc_store, retriever

    if indexer is None or indexer.encoder is None:
        logger.warning("Expansion web omitida: encoder no disponible.")
        return False

    new_docs = expand_corpus_from_query(query, max_new_docs=WEB_EXPANSION_TARGET_DOCS)
    if not new_docs:
        return False

    try:
        indexer.add_documents(new_docs)
        # Recargar store para incluir nuevos docs
        doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)
        if retriever is not None:
            retriever._doc_store = doc_store
        return True
    except Exception as e:
        logger.error(f"Expansion web fallo al reindexar: {e}")
        return False


@app.post("/api/rag_query")
def rag_query(req: RAGQueryRequest):
    """Pipeline RAG directo (legacy)."""
    if not req.query:
        raise HTTPException(status_code=400, detail="Consulta vacía")

    if rag_pipeline is None or not rag_pipeline.is_available:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline no disponible."
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


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _detect_spanish(text: str) -> bool:
    """Detecta si un texto está en español usando marcadores lingüísticos."""
    spanish_markers = {
        "el", "la", "los", "las", "de", "en", "que", "por", "con",
        "una", "síntomas", "tratamiento", "paciente", "enfermedad",
        "diabetes", "presión", "dolor", "cabeza", "tengo", "siento",
        "me duele", "fiebre", "cansancio", "mareo",
    }
    words = set(text.lower().split())
    overlap = len(words & spanish_markers)
    return overlap >= 1


def _build_answer_from_results(results: list, lang: str) -> str:
    """Construye una respuesta conversacional a partir de resultados de retrieval."""
    if not results:
        if lang == "es":
            return "No encontré información relevante sobre tu consulta en mi base de datos. ¿Podrías reformular tu pregunta?"
        return "I couldn't find relevant information about your query in my database. Could you rephrase your question?"

    if lang == "es":
        lines = ["Según la información disponible en mi base de datos:\n"]
        for idx, res in enumerate(results[:5], 1):
            title = res.get("title", "Sin título")
            snippet = res.get("snippet", "")[:200]
            lines.append(f"**[Fuente {idx}]** {title}\n{snippet}\n")
        lines.append("\n_Puedes consultar las fuentes completas en la sección de bibliografía abajo._")
    else:
        lines = ["Based on the information available in my database:\n"]
        for idx, res in enumerate(results[:5], 1):
            title = res.get("title", "Sin título")
            snippet = res.get("snippet", "")[:200]
            lines.append(f"**[Source {idx}]** {title}\n{snippet}\n")
        lines.append("\n_You can check the full sources in the bibliography section below._")

    return "\n".join(lines)


def _answer_indicates_insufficient(answer: str) -> bool:
    """Detecta si el texto indica falta de información en las fuentes."""
    if not answer:
        return False

    text = answer.lower()
    patterns = [
        "no está disponible",
        "no se describen",
        "no proporcionan suficiente",
        "no se encuentra en el texto",
        "sources do not provide",
        "not available in the provided",
        "not described",
        "insufficient information",
    ]
    return any(p in text for p in patterns)


# ---------------------------------------------------------------------------
# Servir frontend estático (producción)
# ---------------------------------------------------------------------------
FRONTEND_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"

if FRONTEND_BUILD_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_BUILD_DIR)), name="static")

    @app.get("/")
    def serve_frontend():
        """Sirve el frontend de React en la raíz (producción)."""
        index_file = FRONTEND_BUILD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "NeuroMedIR API — Frontend no compilado. Ejecute: cd frontend && npm run build"}