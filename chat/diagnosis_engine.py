"""
diagnosis_engine.py — Motor de Diagnóstico Diferencial para NeuroMedIR.

Genera una lista de diagnósticos diferenciales con probabilidades
basándose en los documentos recuperados por el motor híbrido.

Algoritmo:
    1. Recuperar documentos relevantes con el Retriever (BM25 + FAISS + CE)
    2. Extraer nombres de enfermedades/condiciones de los títulos y contenido
       usando heurísticas médicas
    3. Puntuar cada condición según:
       - Score de retrieval del documento que la menciona
       - Bonus para títulos (muy informativos)
    4. Normalizar probabilidades con softmax scaling al rango [0, 100%]
    5. Retornar lista ordenada de diagnósticos con bibliografía

Complejidad:
    - Extracción: O(k * d) donde k = top_k docs, d = doc length
    - Scoring: O(m) donde m = condiciones únicas extraídas
    - Total: Dominado por la recuperación (Stage 1 + 2 del pipeline)
"""

import re
import math
import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter

from .configs import settings as chat_settings

logger = logging.getLogger(__name__)


class DiagnosisEngine:
    """
    Motor de diagnóstico diferencial basado en retrieval.

    Toma los resultados del motor híbrido y genera una lista de
    condiciones médicas probables con porcentajes de probabilidad.

    Uso:
        engine = DiagnosisEngine()
        result = engine.generate_diagnosis(
            query="tengo dolor de cabeza y fiebre",
            retrieval_results=[...documentos del retriever...],
        )
    """

    # Patrones para extraer nombres de condiciones médicas de documentos
    _CONDITION_PATTERNS_ES = [
        r'(?:diagnostico|enfermedad|sindrome|trastorno|condicion)\s+de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})',
        r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,5})\s*[-–—]',
        r'pacientes\s+con\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,3})',
    ]

    _CONDITION_PATTERNS_EN = [
        r'(?:diagnosis|disease|syndrome|disorder|condition)\s+(?:of\s+)?([A-Z][a-z]+(?:\s+[a-z]+){0,4})',
        r'patients\s+with\s+([a-z]+(?:\s+[a-z]+){0,3})',
    ]

    # Palabras vacías que NO son condiciones médicas
    _STOP_CONDITIONS = frozenset({
        'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'en', 'por',
        'con', 'sin', 'que', 'se', 'no', 'si', 'su', 'es', 'son', 'ha',
        'han', 'como', 'entre', 'sobre', 'para', 'desde', 'hasta',
        'paciente', 'pacientes', 'caso', 'casos', 'estudio', 'estudios',
        'resultado', 'resultados', 'tratamiento', 'sintoma', 'sintomas',
        'the', 'a', 'an', 'of', 'in', 'for', 'with', 'without', 'by',
        'from', 'to', 'and', 'or', 'is', 'are', 'was', 'were', 'be',
        'patient', 'patients', 'case', 'cases', 'study', 'studies',
        'result', 'results', 'treatment', 'symptom', 'symptoms',
        'this', 'that', 'these', 'those', 'may', 'can', 'also',
    })

    def __init__(self):
        """Inicializa el motor compilando los patrones de extracción."""
        self._compiled_es = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self._CONDITION_PATTERNS_ES
        ]
        self._compiled_en = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self._CONDITION_PATTERNS_EN
        ]
        logger.info("DiagnosisEngine inicializado con patrones médicos compilados.")

    def generate_diagnosis(
        self,
        query: str,
        retrieval_results: List[Dict],
    ) -> Dict:
        """
        Genera diagnósticos diferenciales con probabilidades.

        Args:
            query: Consulta original del paciente (con síntomas).
            retrieval_results: Resultados del motor híbrido (retriever).

        Returns:
            Diccionario con:
                - diagnoses: Lista de {condition, probability, supporting_docs}
                - bibliography: Lista de documentos usados como referencia
                - summary: Texto resumen del análisis
        """
        if not retrieval_results:
            return {
                "diagnoses": [],
                "bibliography": [],
                "summary": self._no_results_message(query),
            }

        # Paso 1: Extraer condiciones de los documentos recuperados
        condition_scores: Dict[str, float] = Counter()
        condition_docs: Dict[str, List[Dict]] = {}

        for result in retrieval_results:
            score = result.get("score", 0.0)
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            content = f"{title} {snippet}"

            # Extraer condiciones del contenido
            extracted = self._extract_conditions(content)

            for condition in extracted:
                condition_scores[condition] += score
                if condition not in condition_docs:
                    condition_docs[condition] = []
                condition_docs[condition].append({
                    "title": title,
                    "url": result.get("url", "#"),
                    "score": round(score, 4),
                })

        # También usar los títulos como condiciones potenciales (bonus 1.5x)
        for result in retrieval_results:
            title = result.get("title", "")
            score = result.get("score", 0.0)
            title_clean = self._clean_title(title)
            if title_clean and title_clean not in self._STOP_CONDITIONS:
                condition_scores[title_clean] += score * 1.5
                if title_clean not in condition_docs:
                    condition_docs[title_clean] = []
                condition_docs[title_clean].append({
                    "title": title,
                    "url": result.get("url", "#"),
                    "score": round(score, 4),
                })

        # Paso 2: Generar diagnósticos ordenados con probabilidades
        diagnoses = self._compute_probabilities(condition_scores, condition_docs)

        # Paso 3: Construir bibliografía
        bibliography = self._build_bibliography(retrieval_results)

        # Paso 4: Generar resumen
        summary = self._generate_summary(query, diagnoses)

        logger.info(
            f"Diagnóstico generado: {len(diagnoses)} condiciones, "
            f"top='{diagnoses[0]['condition'] if diagnoses else 'N/A'}' "
            f"({diagnoses[0]['probability'] if diagnoses else 0:.1f}% )"
        )

        return {
            "diagnoses": diagnoses,
            "bibliography": bibliography,
            "summary": summary,
        }

    def _extract_conditions(self, text: str) -> List[str]:
        """Extrae nombres de condiciones médicas de un texto."""
        conditions = []

        for pattern in self._compiled_es + self._compiled_en:
            matches = pattern.findall(text)
            for match in matches:
                condition = match.strip()
                if (3 < len(condition) < 60
                        and condition.lower() not in self._STOP_CONDITIONS
                        and not condition.isdigit()):
                    conditions.append(condition)

        return list(set(conditions))

    def _clean_title(self, title: str) -> Optional[str]:
        """Limpia un título para usarlo como condición potencial."""
        if not title or len(title) < 4:
            return None

        clean = title.strip()
        clean = re.sub(r'\s*\(\d{4}\)\s*', '', clean)
        clean = re.sub(
            r'^(review|systematic|meta-analysis|case report|clinical|estudio|'
            r'revisión|informe|análisis|artículo)\s*:?\n+s*',
            '', clean, flags=re.IGNORECASE
        )
        if len(clean) > 80:
            return None

        clean = clean.strip()
        if clean and len(clean) >= 4:
            return clean
        return None

    def _compute_probabilities(
        self,
        condition_scores: Counter,
        condition_docs: Dict[str, List[Dict]],
    ) -> List[Dict]:
        """
        Convierte scores crudos en probabilidades normalizadas usando softmax.

        Algoritmo:
            1. Aplicar softmax: exp(score/temp) / sum(exp(all/temp))
            2. Normalizar a porcentajes (0-100%)
            3. Filtrar por umbral mínimo
            4. Limitar al número máximo configurado
        """
        if not condition_scores:
            return []

        temperature = 0.5

        items = list(condition_scores.items())
        scores_raw = [score for _, score in items]

        max_score = max(scores_raw) if scores_raw else 0
        exp_scores = [
            math.exp((score - max_score) / temperature)
            for score in scores_raw
        ]
        sum_exp = sum(exp_scores)

        diagnoses = []
        for i, (condition, _) in enumerate(items):
            probability = (exp_scores[i] / sum_exp) * 100.0 if sum_exp > 0 else 0.0

            if probability >= chat_settings.MIN_PROBABILIDAD_DIAGNOSTICO:
                diagnoses.append({
                    "condition": condition,
                    "probability": round(probability, 1),
                    "supporting_docs": condition_docs.get(condition, [])[:3],
                })

        diagnoses.sort(key=lambda x: x["probability"], reverse=True)
        diagnoses = diagnoses[:chat_settings.MAX_DIAGNOSTICOS]

        # Renormalizar para que sume ~100%
        total = sum(d["probability"] for d in diagnoses)
        if total > 0:
            for d in diagnoses:
                d["probability"] = round((d["probability"] / total) * 100, 1)

        return diagnoses

    def _build_bibliography(self, retrieval_results: List[Dict]) -> List[Dict]:
        """Construye la lista de referencias/bibliografía."""
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

    def _generate_summary(self, query: str, diagnoses: List[Dict]) -> str:
        """Genera un resumen textual del análisis diagnóstico."""
        if not diagnoses:
            return (
                "No se encontraron condiciones médicas que coincidan "
                "con los síntomas descritos en nuestra base de datos. "
                "Le recomendamos consultar con un profesional de la salud."
            )

        is_spanish = any(
            w in query.lower()
            for w in ["tengo", "siento", "me duele", "dolor", "fiebre",
                       "cansancio", "mareo", "nauseas"]
        )

        if is_spanish:
            lines = ["Basándome en los síntomas que describe, aquí están las posibles condiciones médicas:\n"]
            for i, d in enumerate(diagnoses, 1):
                lines.append(f"**{i}. {d['condition']}** — {d['probability']}%")
                if d.get("supporting_docs"):
                    doc_titles = [f"«{doc['title']}»" for doc in d["supporting_docs"][:2]]
                    lines.append(f"   _Sustentado por: {', '.join(doc_titles)}_")
            lines.append(f"\n{chat_settings.DISCLAIMER_ES}")
        else:
            lines = ["Based on your described symptoms, here are the possible medical conditions:\n"]
            for i, d in enumerate(diagnoses, 1):
                lines.append(f"**{i}. {d['condition']}** — {d['probability']}%")
                if d.get("supporting_docs"):
                    doc_titles = [f'"{doc['title']}"' for doc in d["supporting_docs"][:2]]
                    lines.append(f"   _Supported by: {', '.join(doc_titles)}_")
            lines.append(f"\n{chat_settings.DISCLAIMER_EN}")

        return "\n".join(lines)

    def _no_results_message(self, query: str) -> str:
        """Mensaje cuando no hay resultados de recuperación."""
        return (
            "No se encontraron documentos relevantes en la base de datos "
            "para generar un diagnóstico. Intente describir sus síntomas "
            "de manera más específica o consulte con un profesional de la salud."
        )
