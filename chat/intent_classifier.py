"""
intent_classifier.py — Clasificador de intención para NeuroMedIR.

Clasifica el mensaje del usuario en una de las categorías:
    - SALUDO:     "hola", "buenas", "hello", "hi" → saludo conversacional
    - PREGUNTA:   Pregunta general sobre un tema médico → RAG conversacional
    - SÍNTOMAS:   Describe síntomas o malestares → formulario + diagnóstico
    - DESPEDIDA:  "adiós", "gracias" → despedida + disclaimer
    - NO_MEDICO:  Tema no relacionado con salud → redirección amable

Algoritmo:
    Sistema basado en reglas con scoring ponderado.
    Cada categoría tiene un conjunto de patrones (regex + keywords)
    con pesos asignados. El score final es la suma de los pesos de
    los patrones que hacen match.

    Complejidad: O(n * m) donde n = longitud del mensaje,
    m = número de patrones por categoría.
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
    NO_MEDICO = "no_medico"


# ---------------------------------------------------------------------------
# Patrones de clasificación con pesos
# ---------------------------------------------------------------------------
# Cada patrón es una tupla (regex, peso).

_PATTERNS_SALUDO: List[Tuple[str, float]] = [
    (r'\b(hola|buenas|buenos dias|buenas tardes|buenas noches|hey|ey|que tal|qtal)\b', 1.0),
    (r'\b(hello|hi|hey|good morning|good afternoon|good evening|howdy|greetings)\b', 1.0),
    (r'\b(estas ahi|estas disponible|puedes ayudarme|puedes hablar|estas listo)\b', 0.6),
    (r'\b(are you there|can you help|are you available|are you ready)\b', 0.6),
    # Saludos coloquiales con adjetivos ("hola mi amigo", "buenas gente")
    (r'\b(hola\s+(mi|amigo|amiga|compa|hermano|hermana|gente|chico|chica))\b', 1.2),
]

_PATTERNS_DESPEDIDA: List[Tuple[str, float]] = [
    (r'\b(adios|chao|hasta luego|nos vemos|me voy|bye|goodbye|see you|take care)\b', 1.0),
    (r'\b(gracias|thank you|thanks|muchas gracias|agradezco)\b', 0.7),
]

_PATTERNS_PREGUNTA: List[Tuple[str, float]] = [
    (r'\b(que es|que son|que significa|como se|como funciona|por que|cuales son|cual es|donde)\b', 0.8),
    (r'\b(what is|what are|what does|how does|how do|why is|why do|which are|where is)\b', 0.8),
    (r'\b(definicion|defineme|expliqueme|explica|describe|dime que es|hablame de)\b', 0.7),
    (r'\b(define|explain|describe|tell me about|tell me what)\b', 0.7),
    (r'\b(tratamiento de|causas de|prevencion de|diagnostico de|sintomas de)\b', 0.6),
    (r'\b(treatment of|causes of|prevention of|diagnosis of|symptoms of)\b', 0.6),
]

_PATTERNS_SINTOMAS: List[Tuple[str, float]] = [
    # Primera persona — señal FUERTE
    (r'\b(tengo|siento|me duele|me duelen|me molesta|sufro de|padezco|me pica|me arde)\b', 1.5),
    (r'\b(i have|i feel|im suffering|i suffer|i experience)\b', 1.5),
    # Síntomas comunes en español
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

_PATTERNS_NO_MEDICO: List[Tuple[str, float]] = [
    # Deportes y entretenimiento
    (r'\b(futbol|basketball|beisbol|deporte|jugar|partido|gol|liga)\b', 1.0),
    (r'\b(football|basketball|baseball|sport|game|match|score|league)\b', 1.0),
    # Cocina y recetas
    (r'\b(receta|cocinar|cocina|ingrediente|plato|comida|sopa|pastel)\b', 0.9),
    (r'\b(recipe|cook|kitchen|ingredient|dish|food|soup|cake)\b', 0.9),
    # Clima
    (r'\b(clima|lluvia|soleado|tormenta|temperatura|pronostico)\b', 0.9),
    (r'\b(weather|rain|sunny|storm|temperature|forecast)\b', 0.9),
    # Música y películas
    (r'\b(pelicula|cancion|musica|cantante|actor|pelicula|serie|netflix)\b', 0.9),
    (r'\b(movie|song|music|singer|actor|film|series|netflix)\b', 0.9),
    # Matemáticas y programación
    (r'\b(cuanto es|suma|resta|multiplicacion|division|calcular|ecuacion)\b', 1.0),
    (r'\b(programar|codigo|python|javascript|algoritmo|software)\b', 1.0),
    (r'\b(programming|code|python|javascript|algorithm|software)\b', 1.0),
    # Chistes y temas casuales
    (r'\b(chiste|broma|divertido|risa|humor|contar)\b', 0.8),
    (r'\b(joke|funny|laugh|humor|tell me a)\b', 0.8),
]


class IntentClassifier:
    """
    Clasificador de intención basado en reglas con scoring ponderado.

    Uso:
        classifier = IntentClassifier()
        result = classifier.classify("tengo dolor de cabeza y fiebre")
    """

    def __init__(self):
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
            IntentType.NO_MEDICO: [
                (re.compile(p, re.IGNORECASE), w) for p, w in _PATTERNS_NO_MEDICO
            ],
        }

        logger.info(
            f"IntentClassifier inicializado: "
            f"{sum(len(p) for p in self._patterns.values())} patrones compilados"
        )

    def classify(self, message: str) -> Dict:
        """
        Clasifica un mensaje del usuario en una categoría de intención.

        Args:
            message: Mensaje del usuario (texto libre).

        Returns:
            Diccionario con intent, confidence, scores, detected_symptoms.
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

        # Paso 2: Normalización
        NORMALIZATION_FACTOR = 3.0
        norm_scores: Dict[IntentType, float] = {}
        for intent_type, raw in raw_scores.items():
            norm_scores[intent_type] = min(raw / NORMALIZATION_FACTOR, 1.0)

        # Paso 3: Extraer síntomas detectados
        detected_symptoms = self._extract_symptoms(text)

        # Paso 4: Determinar intención con prioridades
        score_sintomas = norm_scores.get(IntentType.SINTOMAS, 0.0)
        score_pregunta = norm_scores.get(IntentType.PREGUNTA, 0.0)
        score_saludo = norm_scores.get(IntentType.SALUDO, 0.0)
        score_despedida = norm_scores.get(IntentType.DESPEDIDA, 0.0)
        score_no_medico = norm_scores.get(IntentType.NO_MEDICO, 0.0)

        # Lógica de decisión con prioridades:
        # 1. Despedida con score alto → despedida
        # 2. Síntomas por encima del umbral → síntomas (prioridad alta)
        # 3. Pregunta con score significativo → pregunta
        # 4. No médico con score alto → redirigir
        # 5. Saludo → saludo (UMBRAL_SALUDO reducido para "hola mi amigo")
        # 6. Default: si parece sustancial → pregunta, si no → no_medico

        if score_despedida >= chat_settings.UMBRAL_SALUDO:
            intent = IntentType.DESPEDIDA
            confidence = score_despedida
        elif score_sintomas >= chat_settings.UMBRAL_SINTOMA or score_pregunta >= 0.2:
            # Síntomas y preguntas médicas se tratan igual: van al RAG
            intent = IntentType.PREGUNTA
            confidence = max(score_sintomas, score_pregunta)
        elif score_no_medico >= 0.3:
            intent = IntentType.NO_MEDICO
            confidence = score_no_medico
        elif score_saludo >= chat_settings.UMBRAL_SALUDO:
            intent = IntentType.SALUDO
            confidence = score_saludo
        else:
            if len(text) > 15:
                intent = IntentType.PREGUNTA
                confidence = 0.3
            else:
                intent = IntentType.SALUDO
                confidence = 0.4

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
        """Extrae síntomas específicos mencionados en el texto."""
        symptoms = []
        _CONNECTORS = re.compile(r'\s+(y|e|o|u|pero|and|or|but)\s*$')

        symptom_patterns = [
            (r'dolor de (\w+(?:\s+(?!y\s|e\s|o\s|u\s)\w+){0,1})', 'dolor de {}'),
            (r'dolor en (?:el|la|los|las) (\w+(?:\s+\w+){0,1})', 'dolor en {}'),
            (r'me duele[sn]? (?:el|la|los|las) (\w+(?:\s+(?!y\s|e\s|o\s|u\s)\w+){0,1})', 'dolor de {}'),
            (r'estoy con (?:mucha\s+|mucho\s+)?(tos|fiebre|cansancio|nauseas|mareo|vertigo|congestion|diarrea|vomito)', '{}'),
            (r'tengo (fiebre|cansancio|nauseas|mareo|vertigo|tos|congestion|diarrea|vomito)', '{}'),
            (r'\b(tos|fiebre|cansancio|nauseas|mareo|vertigo|congestion|diarrea|vomito)\b', '{}'),
            (r'i have (fever|fatigue|nausea|dizziness|cough|congestion|diarrhea|vomiting)', '{}'),
            (r'my (\w+) hurts?', 'pain in {}'),
            (r'\b(headache|stomachache|sore throat|earache|backache|chest pain)\b', '{}'),
        ]

        for pattern, template in symptom_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cleaned = _CONNECTORS.sub('', match.strip())
                symptom_text = template.format(cleaned)
                if symptom_text not in symptoms and len(symptom_text) > 2:
                    symptoms.append(symptom_text)

        synonym_map = {
            "cough": "tos", "fever": "fiebre", "fatigue": "cansancio",
            "nausea": "nauseas", "dizziness": "mareo", "congestion": "congestion",
            "diarrhea": "diarrea", "vomiting": "vomito",
        }
        normalized = [synonym_map.get(s, s) for s in symptoms]
        return list(dict.fromkeys(normalized))