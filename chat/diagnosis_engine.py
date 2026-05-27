"""
diagnosis_engine.py — Motor de Diagnóstico Diferencial para NeuroMedIR.

Dos modos de diagnóstico:
    1. LLM-driven (preferido): El LLM analiza síntomas + documentos y genera
       un diagnóstico diferencial con razonamiento médico.
    2. Rule-based (fallback): Extracción de condiciones con regex + softmax.

El modo LLM es superior porque:
    - Produce razonamiento médico, no solo nombres de condiciones
    - Las probabilidades reflejan conocimiento médico, no solo scores de retrieval
    - Genera recomendaciones accionables para el paciente
"""

import re
import json
import math
import logging
from typing import List, Dict, Optional
from collections import Counter

from .configs import settings as chat_settings

logger = logging.getLogger(__name__)


class DiagnosisEngine:
    """
    Motor de diagnóstico diferencial.

    Soporta dos modos:
        - LLM-driven (preferido): Usa el LLM para generar diagnósticos con razonamiento.
        - Rule-based (fallback): Usa regex + softmax sobre retrieval scores.
    """

    _CONDITION_PATTERNS_ES = [
        r'(?:diagnostico|enfermedad|sindrome|trastorno|condicion)\s+de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,4})',
        r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,5})\s*[-–—]',
        r'pacientes\s+con\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+){0,3})',
    ]

    _CONDITION_PATTERNS_EN = [
        r'(?:diagnosis|disease|syndrome|disorder|condition)\s+(?:of\s+)?([A-Z][a-z]+(?:\s+[a-z]+){0,4})',
        r'patients\s+with\s+([a-z]+(?:\s+[a-z]+){0,3})',
    ]

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

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: Cliente LLM con método chat(). Si es None, solo funciona en modo rule-based.
        """
        self._llm = llm_client
        self._compiled_es = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self._CONDITION_PATTERNS_ES
        ]
        self._compiled_en = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self._CONDITION_PATTERNS_EN
        ]
        mode = "LLM + rule-based fallback" if llm_client else "rule-based only"
        logger.info(f"DiagnosisEngine inicializado ({mode}).")

    # =========================================================================
    # LLM-DRIVEN DIAGNOSIS (primary method)
    # =========================================================================

    def generate_llm_diagnosis(
        self,
        query: str,
        form_data: dict,
        retrieval_results: List[Dict],
        lang: str = "es",
    ) -> Optional[Dict]:
        """
        Genera un diagnóstico diferencial usando el LLM.

        Args:
            query: Consulta original del paciente.
            form_data: Datos del formulario completado.
            retrieval_results: Resultados del motor híbrido.
            lang: Código de idioma.

        Returns:
            Diccionario con diagnoses, bibliography, summary, o None si falla.
        """
        if self._llm is None or not self._llm.is_available:
            return None

        is_spanish = lang == "es"

        # Construir contexto de documentos recuperados
        docs_text = []
        for idx, res in enumerate(retrieval_results[:10], 1):
            title = res.get("title", "Sin título")
            snippet = res.get("snippet", res.get("content", ""))[:500]
            url = res.get("url", "")
            docs_text.append(f"[Documento {idx}] {title}\n{snippet}\nURL: {url}")

        documents_context = "\n\n".join(docs_text)

        # Construir resumen del formulario
        form_summary_parts = []
        for key, value in form_data.items():
            if key == "original_query":
                continue
            if isinstance(value, list):
                if value:
                    form_summary_parts.append(f"- {key}: {', '.join(str(v) for v in value)}")
            elif value and str(value).strip():
                form_summary_parts.append(f"- {key}: {value}")
        form_summary = "\n".join(form_summary_parts) if form_summary_parts else "Sin datos adicionales del formulario."

        if is_spanish:
            system_prompt = (
                "Eres un médico diagnosticador experto con años de experiencia clínica. "
                "Analiza la información del paciente y los documentos médicos recuperados "
                "para generar un diagnóstico diferencial con probabilidades fundadas en evidencia.\n\n"
                "DEBES responder SOLO con un objeto JSON válido, sin texto adicional.\n\n"
                "El JSON debe tener esta estructura exacta:\n"
                '{\n'
                '  "diagnoses": [\n'
                '    {\n'
                '      "condition": "Nombre de la condición",\n'
                '      "probability": 45.0,\n'
                '      "reasoning": "Explicación de por qué esta condición es probable",\n'
                '      "supporting_evidence": "Evidencia específica de los documentos"\n'
                '    }\n'
                '  ],\n'
                '  "summary": "Resumen general del análisis",\n'
                '  "recommendations": "Recomendaciones para el paciente"\n'
                '}\n\n'
                "Reglas:\n"
                "- Las probabilidades deben sumar aproximadamente 100%\n"
                "- Ordena de más probable a menos probable\n"
                "- Incluye al menos 3 condiciones posibles\n"
                "- Basa tu razonamiento en los documentos cuando sea posible\n"
                "- Si los documentos no son suficientes, indícalo\n"
                "- NUNCA inventes información médica\n"
                "- Incluye un aviso de que esto no sustituye una consulta profesional\n"
            )

            user_message = (
                f"CONSULTA DEL PACIENTE: \"{query}\"\n\n"
                f"DATOS DEL FORMULARIO:\n{form_summary}\n\n"
                f"DOCUMENTOS MÉDICOS RECUPERADOS:\n{documents_context}\n\n"
                "Genera el diagnóstico diferencial. Responde SOLO con el JSON."
            )
        else:
            system_prompt = (
                "You are an expert medical diagnostician with years of clinical experience. "
                "Analyze the patient's information and the retrieved medical documents "
                "to generate a differential diagnosis with evidence-based probabilities.\n\n"
                "You MUST respond ONLY with a valid JSON object, no additional text.\n\n"
                "The JSON must have this exact structure:\n"
                '{\n'
                '  "diagnoses": [\n'
                '    {\n'
                '      "condition": "Condition name",\n'
                '      "probability": 45.0,\n'
                '      "reasoning": "Explanation of why this condition is likely",\n'
                '      "supporting_evidence": "Specific evidence from the documents"\n'
                '    }\n'
                '  ],\n'
                '  "summary": "Overall analysis summary",\n'
                '  "recommendations": "Recommendations for the patient"\n'
                '}\n\n'
                "Rules:\n"
                "- Probabilities should sum to approximately 100%\n"
                "- Order from most likely to least likely\n"
                "- Include at least 3 possible conditions\n"
                "- Base your reasoning on the documents when possible\n"
                "- If documents are insufficient, state it\n"
                "- NEVER invent medical information\n"
                "- Include a disclaimer that this does not replace professional consultation\n"
            )

            user_message = (
                f"PATIENT QUERY: \"{query}\"\n\n"
                f"FORM DATA:\n{form_summary}\n\n"
                f"RETRIEVED MEDICAL DOCUMENTS:\n{documents_context}\n\n"
                "Generate the differential diagnosis. Respond ONLY with the JSON."
            )

        try:
            response = self._llm.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                max_new_tokens=2048,
                json_mode=True,
            )

            if not response:
                logger.warning("LLM diagnosis: empty response.")
                return None

            data = json.loads(response)

            if "diagnoses" not in data or not isinstance(data["diagnoses"], list):
                logger.warning("LLM diagnosis: invalid structure.")
                return None

            # Validar y limpiar diagnósticos
            valid_diagnoses = []
            total_prob = 0.0
            for diag in data["diagnoses"]:
                if not isinstance(diag, dict):
                    continue
                condition = diag.get("condition", "").strip()
                probability = diag.get("probability", 0)
                if not condition:
                    continue
                try:
                    probability = float(probability)
                except (TypeError, ValueError):
                    probability = 0.0

                total_prob += probability
                valid_diagnoses.append({
                    "condition": condition,
                    "probability": round(probability, 1),
                    "reasoning": diag.get("reasoning", ""),
                    "supporting_evidence": diag.get("supporting_evidence", ""),
                    "supporting_docs": [],
                })

            if not valid_diagnoses:
                return None

            # Renormalizar probabilidades si no suman ~100
            if total_prob > 0 and abs(total_prob - 100) > 20:
                for d in valid_diagnoses:
                    d["probability"] = round((d["probability"] / total_prob) * 100, 1)

            # Ordenar por probabilidad
            valid_diagnoses.sort(key=lambda x: x["probability"], reverse=True)
            valid_diagnoses = valid_diagnoses[:chat_settings.MAX_DIAGNOSTICOS]

            # Construir bibliografía
            bibliography = self._build_bibliography(retrieval_results)

            # Summary
            summary = data.get("summary", "")
            recommendations = data.get("recommendations", "")
            if recommendations and is_spanish:
                summary = f"{summary}\n\n**Recomendaciones:** {recommendations}"
            elif recommendations:
                summary = f"{summary}\n\n**Recommendations:** {recommendations}"

            # Agregar disclaimer al summary
            if is_spanish:
                summary += "\n\n⚠️ Esta información no sustituye una consulta médica profesional."
            else:
                summary += "\n\n⚠️ This information does not replace professional medical consultation."

            logger.info(
                f"LLM Diagnosis: {len(valid_diagnoses)} condiciones, "
                f"top='{valid_diagnoses[0]['condition']}' ({valid_diagnoses[0]['probability']}%)"
            )

            return {
                "diagnoses": valid_diagnoses,
                "bibliography": bibliography,
                "summary": summary,
            }

        except json.JSONDecodeError as e:
            logger.error(f"LLM diagnosis: JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM diagnosis failed: {e}")
            return None

    # =========================================================================
    # RULE-BASED DIAGNOSIS (fallback when LLM is unavailable)
    # =========================================================================

    def generate_diagnosis(
        self,
        query: str,
        retrieval_results: List[Dict],
        lang: Optional[str] = None,
    ) -> Dict:
        """Genera diagnósticos usando reglas (fallback)."""
        if not retrieval_results:
            return {
                "diagnoses": [],
                "bibliography": [],
                "summary": self._no_results_message(query),
            }

        condition_scores: Dict[str, float] = Counter()
        condition_docs: Dict[str, List[Dict]] = {}

        for result in retrieval_results:
            score = result.get("score", 0.0)
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            content = f"{title} {snippet}"

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

        diagnoses = self._compute_probabilities(condition_scores, condition_docs)
        bibliography = self._build_bibliography(retrieval_results)
        summary = self._generate_summary(query, diagnoses, lang=lang)

        return {
            "diagnoses": diagnoses,
            "bibliography": bibliography,
            "summary": summary,
        }

    # =========================================================================
    # Shared helpers
    # =========================================================================

    def _extract_conditions(self, text: str) -> List[str]:
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
        if not title or len(title) < 4:
            return None
        clean = title.strip()
        clean = re.sub(r'\s*\(\d{4}\)\s*', '', clean)
        clean = re.sub(
            r'^(review|systematic|meta-analysis|case report|clinical|estudio|'
            r'revisión|informe|análisis|artículo)\s*:?\s*',
            '', clean, flags=re.IGNORECASE
        )
        if len(clean) > 80:
            return None
        clean = clean.strip()
        return clean if len(clean) >= 4 else None

    def _compute_probabilities(
        self,
        condition_scores: Counter,
        condition_docs: Dict[str, List[Dict]],
    ) -> List[Dict]:
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

        total = sum(d["probability"] for d in diagnoses)
        if total > 0:
            for d in diagnoses:
                d["probability"] = round((d["probability"] / total) * 100, 1)

        return diagnoses

    def _build_bibliography(self, retrieval_results: List[Dict]) -> List[Dict]:
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

    def _generate_summary(self, query: str, diagnoses: List[Dict], lang: Optional[str] = None) -> str:
        if not diagnoses:
            return (
                "No se encontraron condiciones médicas que coincidan "
                "con los síntomas descritos en nuestra base de datos. "
                "Le recomendamos consultar con un profesional de la salud."
            )

        is_spanish = True
        if lang in {"es", "en"}:
            is_spanish = lang == "es"
        else:
            is_spanish = any(
                w in query.lower()
                for w in ["tengo", "siento", "me duele", "dolor", "fiebre", "cansancio", "mareo", "nauseas"]
            )

        if is_spanish:
            lines = ["Basándome en los síntomas que describe, aquí están las posibles condiciones médicas:\n"]
            for i, d in enumerate(diagnoses, 1):
                lines.append(f"**{i}. {d['condition']}** — {d['probability']}%")
                if d.get("reasoning"):
                    lines.append(f"   _{d['reasoning']}_")
                if d.get("supporting_docs"):
                    doc_titles = [f"«{doc['title']}»" for doc in d["supporting_docs"][:2]]
                    lines.append(f"   _Sustentado por: {', '.join(doc_titles)}_")
        else:
            lines = ["Based on your described symptoms, here are the possible medical conditions:\n"]
            for i, d in enumerate(diagnoses, 1):
                lines.append(f"**{i}. {d['condition']}** — {d['probability']}%")
                if d.get("reasoning"):
                    lines.append(f"   _{d['reasoning']}_")
                if d.get("supporting_docs"):
                    doc_titles = [f'"{doc["title"]}"' for doc in d["supporting_docs"][:2]]
                    lines.append(f"   _Supported by: {', '.join(doc_titles)}_")

        return "\n".join(lines)

    def _no_results_message(self, query: str) -> str:
        return (
            "No se encontraron documentos relevantes en la base de datos "
            "para generar un diagnóstico. Intente describir sus síntomas "
            "de manera más específica o consulte con un profesional de la salud."
        )