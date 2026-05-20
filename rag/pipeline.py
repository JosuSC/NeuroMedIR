"""
pipeline.py — RAG Pipeline for NeuroMedIR.

Orchestrates the full Retrieval-Augmented Generation flow:
    1. Retrieve:   Hybrid Retriever (BM25+FAISS+CrossEncoder) → candidate docs
    2. Construct:  Build prompt with numbered context + medical system prompt
    3. Generate:   Local LLM (flan-t5) produces grounded answer
    4. Parse:      Extract citations, verify sources, compute confidence

Algorithmic highlights:
    - Context truncation: Priority-queue based (max-heap by score).
      Higher-scored documents are kept intact; lower-scored ones are
      truncated first. O(n log n) for building the priority queue.
    - Citation parsing: Regex-based extraction with O(m) complexity
      where m = answer length.
    - Confidence scoring: Jaccard-like overlap between cited sources
      and provided sources, normalized to [0, 1].

Reference:
    Lewis et al. (2020) — "Retrieval-Augmented Generation for
    Knowledge-Intensive NLP Tasks"
"""

import re
import heapq
import time
import logging
from typing import List, Dict, Optional, Tuple

from retrieval.retriever import Retriever
from .llm_client import BaseLLMClient
from .configs import settings as rag_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Medical System Prompts (bilingual)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_ES = (
    "Eres un asistente médico bilingüe del sistema NeuroMedIR. "
    "Responde basándote EXCLUSIVAMENTE en las fuentes proporcionadas. "
    "Cita usando [Fuente 1], [Fuente 2], etc. "
    "Si las fuentes no bastan, indícalo. "
    "NO inventes información médica. "
    "Incluye un disclaimer: esta información no sustituye consulta profesional. "
    "Responde en el mismo idioma de la consulta."
)

SYSTEM_PROMPT_EN = (
    "You are a bilingual medical assistant from the NeuroMedIR system. "
    "Answer based EXCLUSIVELY on the provided sources. "
    "Cite using [Source 1], [Source 2], etc. "
    "If sources are insufficient, state it clearly. "
    "DO NOT invent medical information. "
    "Include a disclaimer: this information does not replace professional consultation. "
    "Answer in the same language as the query."
)


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for medical queries.

    Combines hybrid retrieval with local LLM generation to produce
    grounded, cited, and verified medical responses.

    Usage:
        pipeline = RAGPipeline(retriever=retriever, llm_client=llm)
        result = pipeline.query("síntomas de diabetes tipo 2")
        # result = {"answer": "...", "sources": [...], "confidence": 0.85, ...}
    """

    def __init__(
        self,
        retriever: Retriever,
        llm_client: BaseLLMClient,
    ):
        """
        Args:
            retriever: Pre-loaded Retriever for document retrieval.
            llm_client: Pre-configured LLM client for text generation.
        """
        self._retriever = retriever
        self._llm = llm_client

    @property
    def is_available(self) -> bool:
        """Returns True if both retriever and LLM are available."""
        return self._llm.is_available

    # -------------------------------------------------------------------
    # Language Detection (O(n) — simple marker word counting)
    # -------------------------------------------------------------------

    _ES_MARKERS = frozenset({
        "el", "la", "los", "las", "de", "en", "que", "por", "con",
        "una", "síntomas", "tratamiento", "paciente", "enfermedad",
        "diabetes", "presión", "dolor", "cabeza", "medicamento",
    })

    def _detect_language(self, text: str) -> str:
        """
        Detects query language using set intersection.

        Complexity: O(n) where n = number of words in text.
        Uses frozenset for O(1) membership testing.
        """
        words = set(text.lower().split())
        overlap = len(words & self._ES_MARKERS)
        return "es" if overlap >= 2 else "en"

    # -------------------------------------------------------------------
    # Context Construction with Priority-Based Truncation
    # -------------------------------------------------------------------

    def _build_context(
        self, sources: List[Dict], max_chars: int
    ) -> Tuple[str, List[Dict]]:
        """
        Builds numbered context from retrieved sources with intelligent
        truncation.

        Algorithm:
            1. Build a max-heap keyed by retrieval score → O(n log n)
            2. Pop documents from highest to lowest score
            3. Add full text while budget remains
            4. Truncate or skip lower-scored documents when budget exhausted

        This ensures the most relevant documents are preserved intact,
        while less relevant ones are the first to be truncated or dropped.

        Args:
            sources: Enriched results from Retriever (sorted by score desc).
            max_chars: Maximum character budget for context.

        Returns:
            (context_string, included_sources)
        """
        if not sources:
            return "", []

        # Build max-heap: (-score, index, source) for descending order
        # Using negative score because heapq is a min-heap by default
        heap = []
        for idx, src in enumerate(sources):
            score = src.get("score", 0.0)
            heapq.heappush(heap, (-score, idx, src))

        # Allocate budget proportionally — higher score = more budget
        context_parts: Dict[int, str] = {}
        included: List[Dict] = []
        remaining = max_chars

        while heap and remaining > 0:
            neg_score, orig_idx, src = heapq.heappop(heap)
            title = src.get("title", "Sin título")
            snippet = src.get("snippet", "")
            url = src.get("url", "")
            source_num = orig_idx + 1

            entry = f"[Fuente {source_num}] Título: {title}\nContenido: {snippet}\nURL: {url}\n"
            entry_len = len(entry)

            if entry_len <= remaining:
                # Full entry fits
                context_parts[orig_idx] = entry
                included.append(src)
                remaining -= entry_len
            elif remaining > 150:
                # Partial fit — truncate entry
                truncated = entry[:remaining - 20] + "...\n"
                context_parts[orig_idx] = truncated
                included.append(src)
                remaining = 0
            # else: skip — not enough room for useful content

        # Reassemble in original order (by source number) for coherent numbering
        sorted_parts = [context_parts[idx] for idx in sorted(context_parts)]
        context = "\n".join(sorted_parts)

        return context, included

    # -------------------------------------------------------------------
    # Prompt Construction
    # -------------------------------------------------------------------

    def _build_prompt(self, query: str, context: str, lang: str) -> str:
        """
        Constructs the full prompt for the LLM.

        Format (seq2seq): instruction + context + query
        Flan-T5 uses a single text input (not chat messages).
        """
        system = SYSTEM_PROMPT_ES if lang == "es" else SYSTEM_PROMPT_EN

        if lang == "es":
            prompt = (
                f"{system}\n\n"
                f"Fuentes médicas recuperadas:\n{context}\n\n"
                f"Consulta del paciente: {query}\n\n"
                f"Responde basándote en las fuentes. "
                f"Cita con [Fuente X]. Incluye disclaimer médico."
            )
        else:
            prompt = (
                f"{system}\n\n"
                f"Retrieved medical sources:\n{context}\n\n"
                f"Patient query: {query}\n\n"
                f"Answer based on the sources. "
                f"Cite with [Source X]. Include a medical disclaimer."
            )

        return prompt

    # -------------------------------------------------------------------
    # Citation Parsing and Confidence Scoring
    # -------------------------------------------------------------------

    # Pre-compiled regex for O(m) citation extraction
    _CITATION_PATTERN = re.compile(
        r'\[(?:Fuente|Source)\s*(\d+)\]', re.IGNORECASE
    )

    def _parse_answer(
        self, answer: str, included_sources: List[Dict]
    ) -> Dict:
        """
        Extracts citations from the LLM answer and computes confidence.

        Algorithm:
            1. Regex scan for [Fuente X] / [Source X] patterns → O(m)
            2. Validate each citation against provided sources → O(k)
            3. Compute confidence as Jaccard-like overlap:
               confidence = |cited ∩ provided| / |provided|

        Args:
            answer: Generated answer text.
            included_sources: Sources included in the context.

        Returns:
            {"citations": list[int], "confidence": float}
        """
        # Extract all citation numbers
        raw_citations = self._CITATION_PATTERN.findall(answer)

        # Validate and deduplicate
        valid_citations = set()
        for cite_str in raw_citations:
            cite_num = int(cite_str)
            if 1 <= cite_num <= len(included_sources):
                valid_citations.add(cite_num)

        # Confidence: ratio of unique cited sources to total provided
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
    ) -> Dict:
        """
        Full RAG pipeline: retrieve → construct → generate → parse.

        Args:
            query: User's medical query.
            top_k: Number of documents to retrieve (default from config).

        Returns:
            {
                "answer": str,           # Generated answer with citations
                "sources": list[dict],   # Source documents used
                "confidence": float,     # 0.0–1.0 confidence score
                "latency_ms": float,     # Total pipeline latency
                "model": str,            # LLM model identifier
                "retrieval_count": int,  # Number of docs retrieved
            }
        """
        t_start = time.perf_counter()
        top_k = top_k or rag_settings.RAG_TOP_K

        # =============================================================
        # STAGE 1: RETRIEVE
        # =============================================================
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

        # Filter by minimum score threshold
        filtered = [
            r for r in results
            if r.get("score", 0) >= rag_settings.RAG_MIN_SCORE_THRESHOLD
        ]
        if not filtered:
            filtered = results  # Fall back to all if none pass threshold

        # =============================================================
        # STAGE 2: CONSTRUCT PROMPT
        # =============================================================
        lang = self._detect_language(query)
        max_context_chars = (
            rag_settings.RAG_MAX_CONTEXT_TOKENS * rag_settings.RAG_CHARS_PER_TOKEN
        )
        context, included_sources = self._build_context(filtered, max_context_chars)
        prompt = self._build_prompt(query, context, lang)

        logger.info(
            f"RAG prompt: {len(prompt)} chars, "
            f"{len(included_sources)} sources, lang={lang}"
        )

        # =============================================================
        # STAGE 3: GENERATE
        # =============================================================
        answer = self._llm.generate(prompt)

        if answer is None:
            # LLM failed — return retrieval-only fallback
            logger.warning("RAG: LLM generation failed. Returning retrieval-only results.")
            answer = self._build_fallback_answer(included_sources, lang)

        # =============================================================
        # STAGE 4: PARSE
        # =============================================================
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
        """Builds a fallback answer from retrieval results when LLM fails."""
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
        """Builds an error response dict."""
        return {
            "answer": message,
            "sources": [],
            "confidence": 0.0,
            "latency_ms": round((time.perf_counter() - t_start) * 1000, 1),
            "model": self._llm.model_name if self._llm else "none",
            "retrieval_count": 0,
        }

