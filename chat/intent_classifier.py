"""
intent_classifier.py — Clasificador de intención para NeuroMedIR.

Clasifica el mensaje del usuario en una de tres categorías:
    - SALUDO:     "hola", "buenas", "hello", "hi" → respuesta conversacional
    - PREGUNTA:   Pregunta general sobre un tema médico → RAG conversacional
    - SÍNTOMAS:   Describe síntomas o malestares → formulario + diagnóstico

Algoritmo:
    Sistema basado en reglas con scoring ponderado.
    Cada categoría tiene un conjunto de patrones (regex + keywords)
    con pesos asignados. El score final es la suma de los pesos de
    los patrones que hacen match.

    La normalización se hace relativa al peso máximo de un solo patrón
    (no la suma total), porque es improbable que TODOS los patrones
    coincidan simultáneamente.

    Complejidad: O(n * m) donde n = longitud del mensaje,
    m = número de patrones por categoría.

Por qué rule-based y no ML:
    - Latencia: 0ms vs 50-200ms de un modelo de clasificación.
    - Sin dependencia de modelos adicionales (ya cargamos 3).
    - Determinista y explicable (crucial en contexto médico).
    - Fácilmente extensible agregando nuevos patrones.
"""

import re
import logging
from typing import Dict, List, Tuple
from enum import Enum

from .configs import settings as chat_settings

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Tipos de intención que el clasificador puede detectar."""
    SALUDO = "saludo"
    PREGUNTA = "pregunta"
    SINTOMAS = "sintomas"
    DESPEDIDA = "despedida"


# ---------------------------------------------------------------------------
# Patrones de clasificación con pesos
# ---------------------------------------------------------------------------
# Cada patrón es una tupla (regex, peso).
# El peso indica la importancia del match:
#   1.0+ = evidencia fuerte
#   0.7-0.9 = evidencia moderada
#   0.3-0.6 = evidencia débil

_PATTERNS_SALUDO: List[Tuple[str, float]] = [
    # Saludos directos en español
    (r'\b(hola|buenas|buenos dias|buenas tardes|buenas noches|hey|ey|que tal|qtal)\b', 1.0),
    # Saludos directos en inglés
    (r'\b(hello|hi|hey|good morning|good afternoon|good evening|howdy|greetings)\b', 1.0),
    # Preguntas de disponibilidad/capacidad
    (r'\b(estas ahi|estas disponible|puedes ayudarme|puedes hablar|estas listo)\b', 0.6),
    (r'\b(are you there|can you help|are you available|are you ready)\b', 0.6),
]

_PATTERNS_DESPEDIDA: List[Tuple[str, float]] = [
    (r'\b(adios|chao|hasta luego|nos vemos|me voy|bye|goodbye|see you|take care)\b', 1.0),
    (r'\b(gracias|thank you|thanks|muchas gracias|agradezco)\b', 0.7),
]

_PATTERNS_PREGUNTA: List[Tuple[str, float]] = [
    # Patrones interrogativos en español
    (r'\b(que es|que son|que significa|como se|como funciona|por que|cuales son|cual es|donde)\b', 0.8),
    # Patrones interrogativos en inglés
    (r'\b(what is|what are|what does|how does|how do|why is|why do|which are|where is)\b', 0.8),
    # Preguntas sobre definiciones o explicaciones
    (r'\b(definicion|defineme|expliqueme|explica|describe|dime que es|hablame de)\b', 0.7),
    (r'\b(define|explain|describe|tell me about|tell me what)\b', 0.7),
    # Preguntas sobre tratamientos/causas (tercera persona, NO primera persona)
    (r'\b(tratamiento de|causas de|prevencion de|diagnostico de|sintomas de)\b', 0.6),
    (r'\b(treatment of|causes of|prevention of|diagnosis of|symptoms of)\b', 0.6),
]

_PATTERNS_SINTOMAS: List[Tuple[str, float]] = [
    # Primera persona — el usuario describe su experiencia (SEÑAL FUERTE)
    (r'\b(tengo|siento|me duele|me duelen|me molesta|sufro de|padezco|me pica|me arde)\b', 1.5),
    (r'\b(i have|i feel|im suffering|i suffer|i experience)\b', 1.5),
    # Síntomas comunes en español (SEÑAL MODERADA-ALTA)
    (r'\b(dolor|fiebre|cansancio|nauseas|mareo|vertigo|tos|congestion|diarrea|vomito)\b', 1.2),
    (r'\b(dificultad para respirar|falta de aire|opresion en el pecho|perdida de olfato|perdida de gusto)\b', 1.5),
    (r'\b(dolor de cabeza|dolor de estomago|dolor de garganta|dolor de oido|dolor de espalda)\b', 1.5),
    (r'\b(dolor de pecho|dolor abdominal|dolor articular|dolor muscular|dolor en el pecho)\b', 1.5),
    # Síntomas comunes en inglés
    (r'\b(pain|fever|fatigue|nausea|dizziness|vertigo|cough|congestion|diarrhea|vomiting)\b', 1.2),
    (r'\b(difficulty breathing|shortness of breath|chest pressure|loss of smell|loss of taste)\b', 1.5),
    (r'\b(headache|stomachache|sore throat|earache|backache|chest pain)\b', 1.5),
    # Localizaciones corporales con primera persona
    (r'\b(me duele (la|el|las|los))\b', 1.5),
    (r'\b(my (head|chest|back|stomach|throat|ear|joint|leg|arm|eye))\b', 1.3),
    # Modificadores de severidad
    (r'\b(muy fuerte|muy intenso|constante|intermitente|severo|cronico|agudo)\b', 0.8),
    (r'\b(very strong|very intense|constant|intermittent|severe|chronic|acute)\b', 0.8),
    # Expresiones de tiempo con síntomas
    (r'\b(desde hace|hace (unos|varios)|llev(o|as) (dias|semanas|meses))\b', 0.7),
    (r'\b(for (days|weeks|months)|since|it started|it began)\b', 0.7),
    # Conectores de síntomas múltiples
    (r'\b(ademas tambien|y tambien me|igualmente me|tambien siento|tambien tengo)\b', 1.0),
    (r'\b(and also|i also|i also have|i also feel|additionally)\b', 1.0),
]


class IntentClassifier:
    """
    Clasificador de intención basado en reglas con scoring ponderado.

    Procesa el mensaje del usuario y devuelve la intención detectada
    junto con un score de confianza para cada categoría.

    Uso:
        classifier = IntentClassifier()
        result = classifier.classify("tengo dolor de cabeza y fiebre")
        # result = {
        #     "intent": "sintomas",
        #     "confidence": 0.85,
        #     "scores": {"saludo": 0.0, "pregunta": 0.1, "sintomas": 0.85, "despedida": 0.0}
        # }
    """

    def __init__(self):
        """Inicializa el clasificador compilando los patrones regex."""
        # Pre-compilar todos los patrones para O(1) matching en runtime
        self._patterns: Dict[IntentType, List[Tuple[re.Pattern, float]]] = {
            IntentType.SALUDO: [
                (re.compile(p, re.IGNORECASE), w) for p, w in _PATTERNS_SALUDO
            ],
            IntentType.DESPEDIDA: [
                (re.compile(p, re.IGNORECASE), w) for p, w in _PATTERNS_DESPEDIDA
            ],
            IntentType.PREGUNTA: [
                (re.compile(p, re.IGNORECASE), w) for p, w in _PATTERNS_PREGUNTA
            ],
            IntentType.SINTOMAS: [
                (re.compile(p, re.IGNORECASE), w) for p, w in _PATTERNS_SINTOMAS
            ],
        }

        logger.info(
            f"IntentClassifier inicializado: "
            f"{sum(len(p) for p in self._patterns.values())} patrones compilados"
        )

    def classify(self, message: str) -> Dict:
        """
        Clasifica un mensaje del usuario en una categoría de intención.

        Algoritmo:
            1. Para cada categoría, calcular score = suma de pesos de matches
            2. Normalizar relativo al máximo peso de un solo patrón (1.5 para síntomas)
            3. Aplicar umbrales para determinar la intención final
            4. Resolver conflictos con prioridad: SÍNTOMAS > DESPEDIDA > PREGUNTA > SALUDO

        Args:
            message: Mensaje del usuario (texto libre).

        Returns:
            Diccionario con:
                - intent: IntentType detectado
                - confidence: Score de confianza [0, 1]
                - scores: Scores detallados por categoría
                - detected_symptoms: Lista de síntomas detectados (si aplica)
        """
        if not message or not message.strip():
            return {
                "intent": IntentType.SALUDO,
                "confidence": 1.0,
                "scores": {t.value: 0.0 for t in IntentType},
                "detected_symptoms": [],
            }

        text = message.strip().lower()

        # Paso 1: Calcular scores crudos por categoría
        raw_scores: Dict[IntentType, float] = {}
        for intent_type, patterns in self._patterns.items():
            score = 0.0
            for pattern, weight in patterns:
                if pattern.search(text):
                    score += weight
            raw_scores[intent_type] = score

        # Paso 2: Normalización relativa
        # El máximo score realista es ~3.0 (2-3 patrones fuertes coincidiendo)
        # Usamos 3.0 como denominador para todas las categorías.
        # Esto produce scores en [0, ~1.0+], que capamos a [0, 1.0].
        NORMALIZATION_FACTOR = 3.0

        norm_scores: Dict[IntentType, float] = {}
        for intent_type, raw in raw_scores.items():
            norm_scores[intent_type] = min(raw / NORMALIZATION_FACTOR, 1.0)

        # Paso 3: Extraer síntomas detectados (para enriquecer el formulario)
        detected_symptoms = self._extract_symptoms(text)

        # Paso 4: Determinar intención con prioridades
        score_sintomas = norm_scores.get(IntentType.SINTOMAS, 0.0)
        score_pregunta = norm_scores.get(IntentType.PREGUNTA, 0.0)
        score_saludo = norm_scores.get(IntentType.SALUDO, 0.0)
        score_despedida = norm_scores.get(IntentType.DESPEDIDA, 0.0)

        # Lógica de decisión con prioridades:
        # 1. Si hay despedida con score alto → despedida
        # 2. Si hay síntomas por encima del umbral → síntomas (prioridad más alta)
        # 3. Si hay pregunta con score significativo → pregunta
        # 4. Si es saludo → saludo
        # 5. Default: pregunta (tratar como consulta general)

        if score_despedida >= chat_settings.UMBRAL_SALUDO:
            intent = IntentType.DESPEDIDA
            confidence = score_despedida
        elif score_sintomas >= chat_settings.UMBRAL_SINTOMA:
            intent = IntentType.SINTOMAS
            confidence = score_sintomas
        elif score_pregunta >= 0.2:
            intent = IntentType.PREGUNTA
            confidence = score_pregunta
        elif score_saludo >= chat_settings.UMBRAL_SALUDO:
            intent = IntentType.SALUDO
            confidence = score_saludo
        else:
            # Si no hay señal clara, y el mensaje es sustancial (>10 chars),
            # tratar como pregunta general. Si es muy corto, saludo.
            if len(text) > 10:
                intent = IntentType.PREGUNTA
                confidence = 0.3
            else:
                intent = IntentType.SALUDO
                confidence = 0.5

        # Construir resultado
        scores_dict = {
            t.value: round(norm_scores.get(t, 0.0), 4)
            for t in IntentType
        }

        logger.info(
            f"Clasificación: '{text[:50]}...' → {intent.value} "
            f"(conf={confidence:.2f}, scores={scores_dict})"
        )

        return {
            "intent": intent,
            "confidence": round(confidence, 4),
            "scores": scores_dict,
            "detected_symptoms": detected_symptoms,
        }

    def _extract_symptoms(self, text: str) -> List[str]:
        """
        Extrae síntomas específicos mencionados en el texto.

        Usa los patrones de síntomas para identificar las frases exactas
        que el paciente mencionó, para incluirlos en el formulario.

        Args:
            text: Texto del mensaje en minúsculas.

        Returns:
            Lista de strings con los síntomas detectados.
        """
        symptoms = []

        # Conectores a excluir del final del síntoma ("y", "e", "o", "u", "pero")
        _CONNECTORS = re.compile(r'\s+(y|e|o|u|pero|and|or|but)\s*$')

        symptom_patterns = [
            # Español: "dolor de X"
            (r'dolor de (\w+(?:\s+(?!y\s|e\s|o\s|u\s)\w+){0,1})', 'dolor de {}'),
            # Español: "me duele el/la X"
            (r'me duele[sn]? (?:el|la|los|las) (\w+(?:\s+(?!y\s|e\s|o\s|u\s)\w+){0,1})', 'dolor de {}'),
            # Español: "estoy con ..."
            (r'estoy con (?:mucha\s+|mucho\s+)?(tos|fiebre|cansancio|nauseas|mareo|vertigo|congestion|diarrea|vomito)', '{}'),
            # Español: "tengo X" (solo para síntomas específicos)
            (r'tengo (fiebre|cansancio|nauseas|mareo|vertigo|tos|congestion|diarrea|vomito)', '{}'),
            # Español: síntomas directos aislados
            (r'\b(tos|fiebre|cansancio|nauseas|mareo|vertigo|congestion|diarrea|vomito)\b', '{}'),
            # Inglés: "I have X"
            (r'i have (fever|fatigue|nausea|dizziness|cough|congestion|diarrhea|vomiting)', '{}'),
            # Inglés: "my X hurts"
            (r'my (\w+) hurts?', 'pain in {}'),
            # Inglés: síntomas directos
            (r'\b(headache|stomachache|sore throat|earache|backache|chest pain)\b', '{}'),
        ]

        for pattern, template in symptom_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cleaned = _CONNECTORS.sub('', match.strip())
                symptom_text = template.format(cleaned)
                # Evitar duplicados y palabras vacías
                if symptom_text not in symptoms and len(symptom_text) > 2:
                    symptoms.append(symptom_text)

        # Normalizar equivalencias EN->ES para mostrar resultados consistentes.
        normalized = []
        synonym_map = {
            "cough": "tos",
            "fever": "fiebre",
            "fatigue": "cansancio",
            "nausea": "nauseas",
            "dizziness": "mareo",
            "congestion": "congestion",
            "diarrhea": "diarrea",
            "vomiting": "vomito",
        }
        for symptom in symptoms:
            normalized.append(synonym_map.get(symptom, symptom))

        # Preservar orden y quitar duplicados.
        return list(dict.fromkeys(normalized))
