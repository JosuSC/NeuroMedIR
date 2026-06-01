"""
api.py — FastAPI endpoints para el sistema NeuroMedIR.

Endpoints:
    GET  /api/health              — Health check del backend
    POST /api/chat                — Endpoint conversacional unificado
    POST /api/chat/submit_form   — Envío de formulario de síntomas
    POST /api/query              — Retrieval híbrido directo (legacy)
    POST /api/rag_query          — Pipeline RAG directo (legacy)

Flujo conversacional (LLM-driven):
    Mensaje del usuario → IntentClassifier → Saludo/Pregunta/Síntomas/NoMédico/Despedida
        - SALUDO:     LLM genera saludo natural + invitación a consultar
        - PREGUNTA:   RAG → respuesta experta + bibliografía
        - SÍNTOMAS:   LLM genera formulario dinámico → [usuario rellena] → LLM diagnóstico
        - NO_MÉDICO:  LLM redirige amablemente a temas médicos
        - DESPEDIDA:  LLM genera despedida + disclaimer
"""

import json
import random
import logging
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
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

from chat.configs import settings as chat_settings
from dynamic_expansion import expand_corpus_from_query
from indexing.configs import settings as idx_settings

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

llm_client = None  # LLM client para uso directo en chat
expansion_retriever: Optional[Retriever] = None  # Índices de expansión web (separados)

# ---------------------------------------------------------------------------
# Configuración de expansión web automática
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





class QueryRequest(BaseModel):
    """Request para retrieval directo (legacy)."""
    query: str


class RAGQueryRequest(BaseModel):
    """Request para RAG directo (legacy)."""
    query: str
    top_k: Optional[int] = None

class FeedbackRequest(BaseModel):
    """Request para retroalimentación por relevancia (Rocchio)."""
    query: str
    results: List[Dict[str, Any]]
    # Cada elemento: {"doc_id": int, "relevant": bool}
    top_k: Optional[int] = None

# ---------------------------------------------------------------------------
# Startup: Inicializar todos los motores
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    """Inicializa todos los motores del sistema al arrancar."""
    global retriever, indexer, doc_store, rag_pipeline
    global intent_classifier, diagnosis_engine, llm_client

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

    from retrieval.query_expansion import QueryExpander
    from retrieval.relevance_feedback import RelevanceFeedback
    from retrieval.ranker import MultiFactorRanker

    retriever = Retriever(
        lexical_index=bm25,
        vector_index=faiss,
        encoder=encoder,
        doc_store=doc_store,
        cleaner=None,
        reranker=reranker,
        expander=QueryExpander(),
        feedback=RelevanceFeedback(),
        ranker=MultiFactorRanker(),
    )

    indexer = Indexer()
    indexer.lexical_index = bm25
    indexer.semantic_index = faiss
    if encoder is not None:
        indexer.encoder = encoder
    indexer.storage = io

    # --- Pipeline RAG (LLM) ---
    try:
        from rag.llm_client import GeminiLLMClient, OpenRouterLLMClient, FallbackLLMClient
        from rag.pipeline import RAGPipeline

        llm_client = FallbackLLMClient([
            OpenRouterLLMClient(),
            GeminiLLMClient(),
        ])
        
        rag_pipeline = RAGPipeline(retriever=retriever, llm_client=llm_client, doc_store=doc_store)
        
        if llm_client.is_available:
            print(f"OK: RAG Pipeline configurado ({llm_client.model_name})")
        else:
            print("Advertencia: no hay LLM configurado. RAG quedará deshabilitado.")
    except ImportError as e:
        print(f"RAG: Módulo no disponible: {e}")
        rag_pipeline = None
        llm_client = None
    except Exception as e:
        print(f"RAG: Error de inicialización: {e}")
        rag_pipeline = None
        llm_client = None

    # --- Clasificador de Intención ---
    intent_classifier = IntentClassifier()
    print("OK: Clasificador de intención inicializado.")

    # --- Retriever de expansión web (índices separados del corpus principal) ---
    global expansion_retriever
    expansion_retriever = _build_expansion_retriever()

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
    Endpoint conversacional unificado — LLM-driven.

    TODAS las respuestas pasan por el LLM cuando está disponible,
    produciendo un flujo conversacional natural y profesional.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    # Clasificar la intención del mensaje
    classification = intent_classifier.classify(req.message)
    intent = classification["intent"]
    detected_symptoms = classification.get("detected_symptoms", [])

    # Detectar idioma
    requested_lang = req.lang if req.lang in {"es", "en"} else None
    is_spanish = True if requested_lang == "es" else False if requested_lang == "en" else _detect_spanish(req.message)
    lang_code = "es" if is_spanish else "en"

    # ============================================================
    # SALUDO → LLM genera saludo natural
    # ============================================================
    if intent == IntentType.SALUDO:
        return _handle_greeting_llm(req.message, lang_code)

    # ============================================================
    # DESPEDIDA → LLM genera despedida + disclaimer
    # ============================================================
    if intent == IntentType.DESPEDIDA:
        return _handle_farewell_llm(req.message, lang_code)

    # ============================================================
    # NO_MÉDICO → LLM redirige amablemente
    # ============================================================
    if intent == IntentType.NO_MEDICO:
        return _handle_non_medical_llm(req.message, lang_code)

    # ============================================================
    # SÍNTOMAS → Se trata como pregunta médica (RAG + retrieval)
    # ============================================================
    if intent == IntentType.SINTOMAS:
        return _handle_question(req.message, lang_code)

    # ============================================================
    # PREGUNTA → RAG conversacional + bibliografía
    # ============================================================
    if intent == IntentType.PREGUNTA:
        return _handle_question(req.message, lang_code)

    # Fallback
    return _handle_greeting_llm(req.message, lang_code)


# ---------------------------------------------------------------------------
# Handlers con LLM
# ---------------------------------------------------------------------------

def _handle_greeting_llm(message: str, lang_code: str) -> dict:
    """Usa el LLM para generar un saludo natural y profesional."""
    is_spanish = lang_code == "es"

    if llm_client and llm_client.is_available:
        try:
            if is_spanish:
                system_prompt = chat_settings.SYSTEM_PROMPT_MEDICAL_ES
                user_msg = (
                    f"El usuario te saluda: \"{message}\"\n\n"
                    "Responde con un saludo cálido y profesional. Preséntate brevemente como NeuroMedIR "
                    "y menciona que puedes ayudar con consultas médicas, síntomas, enfermedades, "
                    "tratamientos, prevención, etc. Sé conversacional y amigable."
                )
            else:
                system_prompt = chat_settings.SYSTEM_PROMPT_MEDICAL_EN
                user_msg = (
                    f"The user greets you: \"{message}\"\n\n"
                    "Respond with a warm, professional greeting. Briefly introduce yourself as NeuroMedIR "
                    "and mention you can help with medical queries, symptoms, diseases, "
                    "treatments, prevention, etc. Be conversational and friendly."
                )

            response = llm_client.chat(system_prompt, user_msg, max_new_tokens=512)

            if response:
                return {
                    "type": "greeting",
                    "message": response,
                    "form_schema": None,
                    "diagnoses": None,
                    "bibliography": None,
                }
        except Exception as e:
            logger.error(f"LLM greeting failed: {e}")

    # Fallback: saludos predefinidos
    greetings = chat_settings.SALUDOS_ES if is_spanish else chat_settings.SALUDOS_EN
    return {
        "type": "greeting",
        "message": random.choice(greetings),
        "form_schema": None,
        "diagnoses": None,
        "bibliography": None,
    }


def _handle_farewell_llm(message: str, lang_code: str) -> dict:
    """Usa el LLM para generar una despedida profesional con disclaimer."""
    is_spanish = lang_code == "es"

    if llm_client and llm_client.is_available:
        try:
            if is_spanish:
                system_prompt = chat_settings.SYSTEM_PROMPT_MEDICAL_ES
                user_msg = (
                    f"El usuario se despide: \"{message}\"\n\n"
                    "Despídete profesionalmente. Incluye un aviso importante de que "
                    "tu información no sustituye una consulta médica profesional. "
                    "Sé cálido y preocupado por el bienestar del paciente."
                )
            else:
                system_prompt = chat_settings.SYSTEM_PROMPT_MEDICAL_EN
                user_msg = (
                    f"The user says goodbye: \"{message}\"\n\n"
                    "Say goodbye professionally. Include an important disclaimer that "
                    "your information does not replace professional medical consultation. "
                    "Be warm and caring about the patient's wellbeing."
                )

            response = llm_client.chat(system_prompt, user_msg, max_new_tokens=512)

            if response:
                return {
                    "type": "farewell",
                    "message": response,
                    "form_schema": None,
                    "diagnoses": None,
                    "bibliography": None,
                }
        except Exception as e:
            logger.error(f"LLM farewell failed: {e}")

    farewells = chat_settings.DESPEDIDAS_ES if is_spanish else chat_settings.DESPEDIDAS_EN
    return {
        "type": "farewell",
        "message": random.choice(farewells),
        "form_schema": None,
        "diagnoses": None,
        "bibliography": None,
    }


def _handle_non_medical_llm(message: str, lang_code: str) -> dict:
    """Usa el LLM para redirigir amablemente a temas médicos."""
    is_spanish = lang_code == "es"

    if llm_client and llm_client.is_available:
        try:
            if is_spanish:
                system_prompt = chat_settings.SYSTEM_PROMPT_MEDICAL_ES
                user_msg = (
                    f"El usuario pregunta algo que no es médico: \"{message}\"\n\n"
                    "Explica amablemente que eres un asistente especializado en salud y que "
                    "tu función es ayudar con consultas médicas. Menciona ejemplos de lo que "
                    "SÍ puedes hacer: responder sobre síntomas, enfermedades, tratamientos, "
                    "prevención, contagiología, etc. Sé amable pero claro en tu redirección."
                )
            else:
                system_prompt = chat_settings.SYSTEM_PROMPT_MEDICAL_EN
                user_msg = (
                    f"The user asks something non-medical: \"{message}\"\n\n"
                    "Kindly explain that you are a health-specialized assistant and that "
                    "your function is to help with medical queries. Mention examples of what "
                    "you CAN do: answer about symptoms, diseases, treatments, "
                    "prevention, contagion, etc. Be kind but clear in your redirection."
                )

            response = llm_client.chat(system_prompt, user_msg, max_new_tokens=512)

            if response:
                return {
                    "type": "greeting",
                    "message": response,
                    "form_schema": None,
                    "diagnoses": None,
                    "bibliography": None,
                }
        except Exception as e:
            logger.error(f"LLM non-medical redirect failed: {e}")

    no_med = chat_settings.NO_MEDICO_ES if is_spanish else chat_settings.NO_MEDICO_EN
    return {
        "type": "greeting",
        "message": random.choice(no_med),
        "form_schema": None,
        "diagnoses": None,
        "bibliography": None,
    }





def _handle_question(message: str, lang_code: str) -> dict:
    """Maneja preguntas generales: RAG → respuesta experta + bibliografía."""
    t_start = time.time()
    used_web_search = False

    try:
        initial_results = retriever.retrieve(message, top_k=5, preferred_lang=lang_code)
        # Complementar con resultados de expansión si existen
        if expansion_retriever is not None:
            try:
                exp_results = expansion_retriever.retrieve(message, top_k=3, preferred_lang=lang_code)
                initial_results = initial_results + exp_results
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Retrieval inicial falló: {e}")
        initial_results = []

    if _should_expand(initial_results):
        used_web_search = _try_expand_corpus(message)

    # Intentar RAG (genera respuesta natural con LLM)
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

    # Si la respuesta indica insuficiencia, intentar expansión web
    if answer_text and _answer_indicates_insufficient(answer_text):
        if not used_web_search:
            used_web_search = _try_expand_corpus(message)
        if used_web_search and rag_pipeline is not None and rag_pipeline.is_available:
            try:
                rag_result = rag_pipeline.query(message, top_k=5, lang=lang_code)
                answer_text = rag_result.get("answer")
                sources = rag_result.get("sources", [])
                sources = _filter_by_language(sources, lang_code)
                confidence = rag_result.get("confidence", 0.0)
            except Exception as e:
                logger.error(f"RAG falló tras expansión web: {e}")

    # Si hay baja confianza, intentar expansión web
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
        results = retriever.retrieve(message, top_k=5, preferred_lang=lang_code)
        sources = results
        answer_text = _build_answer_from_results(results, lang_code)

    # Construir bibliografía
    bibliography = _build_bibliography(sources) if sources else []

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
# Legacy endpoints
# ---------------------------------------------------------------------------

@app.post("/api/query")
def process_query(req: QueryRequest):
    """Retrieval híbrido directo (legacy)."""
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
# Retroalimentación por relevancia (Rocchio)
# ---------------------------------------------------------------------------

@app.post("/api/feedback")
def feedback_endpoint(req: FeedbackRequest):
    """
    Recibe feedback explícito del usuario sobre resultados previos
    y devuelve una lista re-rankeada usando ajuste Rocchio.

    Body:
        {
            "query": "síntomas de diabetes",
            "results": [
                {"doc_id": 42, "relevant": true},
                {"doc_id": 17, "relevant": false}
            ],
            "top_k": 10
        }
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query vacía.")

    if not req.results:
        raise HTTPException(status_code=400, detail="Lista de feedback vacía.")

    # Construir feedback_map: {doc_id: bool}
    feedback_map: Dict[int, bool] = {}
    for item in req.results:
        doc_id = item.get("doc_id")
        relevant = item.get("relevant")
        if doc_id is None or relevant is None:
            raise HTTPException(
                status_code=422,
                detail="Cada resultado debe tener 'doc_id' (int) y 'relevant' (bool)."
            )
        feedback_map[int(doc_id)] = bool(relevant)

    try:
        results = retriever.retrieve_with_feedback(
            query=req.query,
            feedback_map=feedback_map,
            top_k=req.top_k,
        )
    except Exception as e:
        logger.error(f"Feedback endpoint falló: {e}")
        raise HTTPException(status_code=500, detail=f"Error en retroalimentación: {e}")

    return {
        "type": "feedback",
        "query": req.query,
        "results": results,
        "feedback_applied": len(feedback_map),
    }

# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _should_expand(results: list) -> bool:
    """Retorna True si la base local es insuficiente para responder."""
    if results is None:
        return True
    if len(results) < MIN_RESULTS_FOR_ANSWER:
        return True
    top_score = results[0].get("score", 0.0) if results else 0.0
    return top_score < 0.15


def _build_bibliography(retrieval_results: list) -> list:
    """Construye la bibliografía a partir de los resultados del retrieval."""
    bibliography = []
    seen_titles = set()
    for idx, result in enumerate(retrieval_results, 1):
        title = result.get("title", "Sin título")
        if title in seen_titles:
            continue
        seen_titles.add(title)
        bibliography.append({
            "ref_num": idx,
            "title": title,
            "url": result.get("url", "#"),
            "source": result.get("source", ""),
            "category": result.get("category", "other"),
            "snippet": (result.get("snippet", ""))[:150] + "...",
        })
    return bibliography

def _build_expansion_retriever() -> Optional[Retriever]:
    """
    Construye un Retriever independiente sobre los índices de expansión web.
    Si los índices no existen aún, retorna None (se crean en el primer expand).
    """
    try:
        exp_bm25 = BM25Index(
            k1=idx_settings.BM25_PARAMS["k1"],
            b=idx_settings.BM25_PARAMS["b"],
        )
        exp_faiss = FAISSHNSWIndex(
            dimension=idx_settings.EMBEDDING_DIM,
            m=idx_settings.HNSW_M,
            ef_construction=idx_settings.HNSW_EF_CONSTRUCTION,
        )
        exp_encoder = None
        try:
            exp_encoder = TextEncoder(idx_settings.EMBEDDING_MODEL_NAME)
        except Exception as e:
            logger.warning(f"Expansion retriever: encoder no disponible: {e}")

        exp_doc_store = DocumentStore(idx_settings.EXPANSION_DATA_DIR)
        exp_storage = IndexStorage(str(idx_settings.EXPANSION_INDEX_DIR))

        lex_ok = exp_storage.load_lexical(exp_bm25)
        vec_ok = exp_storage.load_vector(exp_faiss)

        if not (lex_ok and vec_ok):
            logger.info("Expansion indices not found yet — will be created on first expand.")
            return None

        if exp_doc_store.count == 0:
            logger.info("Expansion doc_store is empty — skipping expansion retriever.")
            return None

        return Retriever(exp_bm25, exp_faiss, exp_encoder, exp_doc_store)
    except Exception as e:
        logger.error(f"Failed to build expansion retriever: {e}")
        return None


def _try_expand_corpus(query: str) -> bool:
    """
    Ejecuta expansión web e indexa los nuevos documentos en índices
    SEPARADOS del corpus principal (indicación del profesor).

    El expansion_retriever se reconstruye tras cada expansión para
    incluir los nuevos documentos en búsquedas futuras.
    """
    global expansion_retriever

    new_docs = expand_corpus_from_query(query, max_new_docs=WEB_EXPANSION_TARGET_DOCS)
    if not new_docs:
        return False

    try:
        # Indexer exclusivo para expansión — rutas separadas
        exp_indexer = Indexer()
        exp_indexer.storage = IndexStorage(str(idx_settings.EXPANSION_INDEX_DIR))

        # Si ya existen índices de expansión, cargarlos para agregar incrementalmente
        exp_indexer.load_indices()

        

        exp_indexer.add_documents(new_docs)

        # Reconstruir expansion_retriever con los nuevos índices
        expansion_retriever = _build_expansion_retriever()

        logger.info(f"Expansión web: {len(new_docs)} docs indexados en índices separados.")
        return True

    except Exception as e:
        logger.error(f"Expansión web falló al reindexar: {e}")
        return False


def _detect_spanish(text: str) -> bool:
    spanish_markers = {
        "el", "la", "los", "las", "de", "en", "que", "por", "con",
        "una", "síntomas", "tratamiento", "paciente", "enfermedad",
        "diabetes", "presión", "dolor", "cabeza", "tengo", "siento",
        "me duele", "fiebre", "cansancio", "mareo",
    }
    words = set(text.lower().split())
    overlap = len(words & spanish_markers)
    return overlap >= 1

def _filter_by_language(results: list, lang_code: str, min_results: int = 3) -> list:
    """Filtra resultados por idioma."""
    if not results:
        return results

    NOISE_TITLES = {
        "health topics", "temas de salud", "síntomas", "symptoms",
        "no results for", "sin resultados"
    }

    def is_noise(r):
        title = r.get("title", "").lower()
        return any(noise in title for noise in NOISE_TITLES)

    def is_target_lang(r):
        source = r.get("source", "").lower()
        title = r.get("title", "").lower()
        if lang_code == "es":
            return ("español" in source or "es" in source or
                    "español" in title or "en español" in title)
        else:
            return ("nhs" in source or
                    ("medlineplus" in source and "español" not in source and "es" not in source))

    filtered = [r for r in results if not is_noise(r) and is_target_lang(r)]
    return filtered if len(filtered) >= min_results else [r for r in results if not is_noise(r)]


def _build_answer_from_results(results: list, lang: str) -> str:
    if not results:
        if lang == "es":
            return "No encontré información relevante sobre tu consulta en mi base de datos. ¿Podrías reformular tu pregunta?"
        return "I couldn't find relevant information about your query in my database. Could you rephrase?"

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
        index_file = FRONTEND_BUILD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "NeuroMedIR API — Frontend no compilado."}