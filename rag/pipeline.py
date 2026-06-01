"""
pipeline.py — RAG Pipeline for NeuroMedIR.

Orchestrates the full Retrieval-Augmented Generation flow:
    1. Retrieve:   Hybrid Retriever (BM25+FAISS+CrossEncoder) → candidate docs
    2. Construct:  Build prompt with numbered context + medical system prompt
    3. Generate:   Gemini LLM produces grounded answer
    4. Parse:      Extract citations, verify sources, compute confidence
"""

import re
import heapq
import time
import logging
from typing import List, Dict, Optional, Tuple

from retrieval.retriever import Retriever
from rag.llm_client import BaseLLMClient
from rag.configs import settings as rag_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Medical System Prompts — Mejorados para respuestas expertas y conversacionales
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_ES = (
    "Eres NeuroMedIR, un asistente médico virtual profesional y empático. "
    "Respondes como un médico experimentado que se preocupa por su paciente. "
    "Explicas con DETALLE y CLARIDAD, usando lenguaje accesible pero preciso. "
    "Si la pregunta es sobre síntomas, explica cada síntoma con detalle: qué es, "
    "por qué ocurre, cuándo preocuparse y cuándo no. "
    "Si la pregunta es sobre una enfermedad, cubre: definición, causas, síntomas, "
    "diagnóstico, tratamiento, prevención y pronóstico. "
    "Si la pregunta es sobre contagio, explica las vías de transmisión con claridad. "
    "Responde basándote EXCLUSIVAMENTE en las fuentes proporcionadas. "
    "Cita usando [Fuente 1], [Fuente 2], etc. "
    "Si las fuentes no bastan para responder completamente, indícalo y ofrece lo que sí puedes decir. "
    "NO inventes información médica. "
    "Incluye un disclaimer: esta información no sustituye consulta profesional. "
    "Responde en español."
)

SYSTEM_PROMPT_EN = (
    "You are NeuroMedIR, a professional and empathetic virtual medical assistant. "
    "You respond like an experienced doctor who cares about their patient. "
    "You explain in DETAIL and with CLARITY, using accessible yet precise language. "
    "If the question is about symptoms, explain each symptom in detail: what it is, "
    "why it occurs, when to worry and when not to. "
    "If the question is about a disease, cover: definition, causes, symptoms, "
    "diagnosis, treatment, prevention, and prognosis. "
    "If the question is about transmission, explain the routes clearly. "
    "Answer based EXCLUSIVELY on the provided sources. "
    "Cite using [Source 1], [Source 2], etc. "
    "If sources are insufficient to answer completely, state it and offer what you can say. "
    "DO NOT invent medical information. "
    "Include a disclaimer: this information does not replace professional consultation. "
    "Answer in English."
)


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for medical queries.
    """

    def __init__(self, retriever: Retriever, llm_client: BaseLLMClient, doc_store=None):
        self._retriever = retriever
        self._llm = llm_client
        self._doc_store = doc_store  # Para recuperar contenido completo de documentos

    @property
    def is_available(self) -> bool:
        return self._llm.is_available

    @property
    def llm(self) -> BaseLLMClient:
        """Exponer el LLM client para uso desde api.py en otros modos de chat."""
        return self._llm

    # -------------------------------------------------------------------
    # Language Detection
    # -------------------------------------------------------------------

    _ES_MARKERS = frozenset({
        "el", "la", "los", "las", "de", "en", "que", "por", "con",
        "una", "síntomas", "tratamiento", "paciente", "enfermedad",
        "diabetes", "presión", "dolor", "cabeza", "medicamento",
        "tengo", "siento", "me duele", "fiebre",
    })

    def _detect_language(self, text: str) -> str:
        words = set(text.lower().split())
        overlap = len(words & self._ES_MARKERS)
        return "es" if overlap >= 1 else "en"

    # -------------------------------------------------------------------
    # Context Construction with Priority-Based Truncation
    # -------------------------------------------------------------------

    def _build_context(
        self, sources: List[Dict], max_chars: int
    ) -> Tuple[str, List[Dict]]:
        if not sources:
            return "", []

        heap = []
        for idx, src in enumerate(sources):
            score = src.get("score", 0.0)
            heapq.heappush(heap, (-score, idx, src))

        context_parts: Dict[int, str] = {}
        included: List[Dict] = []
        remaining = max_chars

        while heap and remaining > 0:
            neg_score, orig_idx, src = heapq.heappop(heap)
            title = src.get("title", "Sin título")
            url = src.get("url", "")
            source_num = orig_idx + 1

            # Intentar contenido completo desde el doc_store
            content = ""
            doc_id = src.get("doc_id")
            if self._doc_store and doc_id is not None:
                content = self._doc_store.get_text(doc_id)

            # Fallback al snippet si no hay doc_store o el doc no se encontró
            if not content:
                content = src.get("snippet", "")

            entry = f"[Fuente {source_num}] Título: {title}\nContenido: {content}\nURL: {url}\n"
            entry_len = len(entry)

            if entry_len <= remaining:
                context_parts[orig_idx] = entry
                included.append(src)
                remaining -= entry_len
            elif remaining > 150:
                truncated = entry[:remaining - 20] + "...\n"
                context_parts[orig_idx] = truncated
                included.append(src)
                remaining = 0

        sorted_parts = [context_parts[idx] for idx in sorted(context_parts)]
        context = "\n".join(sorted_parts)

        return context, included

    # -------------------------------------------------------------------
    # Prompt Construction
    # -------------------------------------------------------------------

    def _build_prompt(self, query: str, context: str, lang: str) -> str:
        system = SYSTEM_PROMPT_ES if lang == "es" else SYSTEM_PROMPT_EN

        if lang == "es":
            prompt = (
                f"{system}\n\n"
                "Idioma de respuesta: Español.\n\n"
                f"Fuentes médicas recuperadas:\n{context}\n\n"
                f"Consulta del paciente: {query}\n\n"
                f"Responde basándote en las fuentes. Cita con [Fuente X]. "
                f"Si las fuentes son insuficientes para responder completamente, "
                f"indícalo y ofrece la información parcial que sí puedes proporcionar. "
                f"Incluye disclaimer médico."
            )
        else:
            prompt = (
                f"{system}\n\n"
                "Response language: English.\n\n"
                f"Retrieved medical sources:\n{context}\n\n"
                f"Patient query: {query}\n\n"
                f"Answer based on the sources. Cite with [Source X]. "
                f"If sources are insufficient to answer completely, "
                f"state it and offer the partial information you can provide. "
                f"Include a medical disclaimer."
            )

        return prompt

    # -------------------------------------------------------------------
    # Completion Guard
    # -------------------------------------------------------------------

    def _needs_continuation(self, answer: str) -> bool:
        if not answer:
            return False
        text = answer.strip()
        min_chars = rag_settings.RAG_MIN_NEW_TOKENS * rag_settings.RAG_CHARS_PER_TOKEN
        if len(text) < min_chars:
            return True
        if text.endswith(("...", "…")):
            return True
        terminal_chars = (".", "!", "?", "]", ")", "\"", "”", "’")
        return text[-1] not in terminal_chars

    def _continue_answer(self, answer: str, lang: str) -> Optional[str]:
        if lang == "es":
            prompt = (
                "Continua la respuesta a partir del texto dado. "
                "Termina la ultima frase si esta incompleta. "
                "No repitas contenido previo.\n\n"
                f"Respuesta actual:\n{answer}\n\nContinuacion:"
            )
        else:
            prompt = (
                "Continue the answer from the given text. "
                "Finish the last sentence if it is incomplete. "
                "Do not repeat previous content.\n\n"
                f"Current answer:\n{answer}\n\nContinuation:"
            )
        return self._llm.generate(
            prompt,
            max_new_tokens=rag_settings.RAG_CONTINUATION_MAX_TOKENS,
        )

    def _ensure_complete_answer(self, answer: str, lang: str) -> str:
        if not self._needs_continuation(answer):
            return answer
        merged = answer
        for _ in range(rag_settings.RAG_CONTINUATION_MAX_ATTEMPTS):
            if not self._needs_continuation(merged):
                break
            continuation = self._continue_answer(merged, lang)
            if not continuation:
                break
            merged = f"{merged.rstrip()} {continuation.lstrip()}"
            if len(merged) <= len(answer) + 5:
                break
        return merged

    # -------------------------------------------------------------------
    # Citation Parsing and Confidence Scoring
    # -------------------------------------------------------------------

    _CITATION_PATTERN = re.compile(
        r'\[(?:Fuente|Source)\s*(\d+)\]', re.IGNORECASE
    )

    def _parse_answer(
        self, answer: str, included_sources: List[Dict]
    ) -> Dict:
        raw_citations = self._CITATION_PATTERN.findall(answer)
        valid_citations = set()
        for cite_str in raw_citations:
            cite_num = int(cite_str)
            if 1 <= cite_num <= len(included_sources):
                valid_citations.add(cite_num)

        total_provided = len(included_sources)
        confidence = len(valid_citations) / total_provided if total_provided > 0 else 0.0

        return {
            "citations": sorted(valid_citations),
            "confidence": round(min(confidence, 1.0), 2),
        }

    # -------------------------------------------------------------------
    # Main Pipeline
    # -------------------------------------------------------------------

    def query(
        self,
        query: str,
        top_k: Optional[int] = None,
        lang: Optional[str] = None,
    ) -> Dict:
        """Full RAG pipeline: retrieve → construct → generate → parse."""
        t_start = time.perf_counter()
        top_k = top_k or rag_settings.RAG_TOP_K

        # STAGE 1: RETRIEVE
        try:
            results = self._retriever.retrieve(query, top_k=top_k)
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return self._error_response(
                "Error al recuperar documentos. Intente nuevamente.",
                t_start,
            )

        if not results:
            return self._error_response(
                "No se encontraron documentos relevantes para su consulta.",
                t_start,
            )

        filtered = [
            r for r in results
            if r.get("score", 0) >= rag_settings.RAG_MIN_SCORE_THRESHOLD
        ]
        if not filtered:
            filtered = results

        # Filtrar docs con muy poco contenido real (videos sin transcripción,
        # páginas índice, etc.) que hacen match léxico por título pero no
        # aportan información sustancial al LLM.
        if self._doc_store:
            substantial = []
            for r in filtered:
                doc_id = r.get("doc_id")
                content = self._doc_store.get_text(doc_id) if doc_id is not None else ""
                if len(content) >= rag_settings.RAG_MIN_DOC_CONTENT_CHARS:
                    substantial.append(r)
            # Solo aplicar el filtro si quedan suficientes docs
            if len(substantial) >= 2:
                filtered = substantial

        # STAGE 2: CONSTRUCT PROMPT
        lang = lang if lang in {"es", "en"} else self._detect_language(query)
        max_context_chars = (
            rag_settings.RAG_MAX_CONTEXT_TOKENS * rag_settings.RAG_CHARS_PER_TOKEN
        )
        context, included_sources = self._build_context(filtered, max_context_chars)
        prompt = self._build_prompt(query, context, lang)

        logger.info(
            f"RAG prompt: {len(prompt)} chars, "
            f"{len(included_sources)} sources, lang={lang}"
        )

        # STAGE 3: GENERATE — Intentar chat() primero (mejor calidad), fallback a generate()
        answer = None

        # Intentar chat con system prompt separado (mejor calidad)
        system = SYSTEM_PROMPT_ES if lang == "es" else SYSTEM_PROMPT_EN
        if lang == "es":
            user_msg = (
                f"Fuentes médicas recuperadas:\n{context}\n\n"
                f"Consulta del paciente: {query}\n\n"
                f"Responde basándote en las fuentes. Cita con [Fuente X]. "
                f"Incluye disclaimer médico."
            )
        else:
            user_msg = (
                f"Retrieved medical sources:\n{context}\n\n"
                f"Patient query: {query}\n\n"
                f"Answer based on the sources. Cite with [Source X]. "
                f"Include a medical disclaimer."
            )

        answer = self._llm.chat(system, user_msg, max_new_tokens=rag_settings.RAG_MAX_NEW_TOKENS)

        if answer:
            answer = self._ensure_complete_answer(answer, lang)

        if answer is None:
            # Fallback al generate() legacy
            answer = self._llm.generate(prompt)

        if answer is None:
            logger.warning("RAG: LLM generation failed. Returning retrieval-only results.")
            answer = self._build_fallback_answer(included_sources, lang)

        # STAGE 4: PARSE
        parsed = self._parse_answer(answer, included_sources)

        latency_ms = round((time.perf_counter() - t_start) * 1000, 1)

        logger.info(
            f"RAG completed in {latency_ms}ms — "
            f"retrieval: {len(results)}, "
            f"context_sources: {len(included_sources)}, "
            f"citations: {len(parsed['citations'])}, "
            f"confidence: {parsed['confidence']}"
        )

        return {
            "answer": answer,
            "sources": included_sources,
            "confidence": parsed["confidence"],
            "latency_ms": latency_ms,
            "model": self._llm.model_name,
            "retrieval_count": len(results),
        }

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _build_fallback_answer(
        self, sources: List[Dict], lang: str
    ) -> str:
        lines = []
        for idx, src in enumerate(sources, 1):
            title = src.get("title", "Sin título")
            snippet = src.get("snippet", "")[:200]
            lines.append(f"[Fuente {idx}] {title}: {snippet}")

        answer = "\n\n".join(lines)

        if lang == "es":
            answer += (
                "\n\n⚠️ Nota: La generación con IA no está disponible. "
                "Mostrando resultados de recuperación directa."
            )
        else:
            answer += (
                "\n\n⚠️ Note: AI generation is unavailable. "
                "Showing direct retrieval results."
            )

        return answer

    def _error_response(self, message: str, t_start: float) -> Dict:
        return {
            "answer": message,
            "sources": [],
            "confidence": 0.0,
            "latency_ms": round((time.perf_counter() - t_start) * 1000, 1),
            "model": self._llm.model_name if self._llm else "none",
            "retrieval_count": 0,
        }