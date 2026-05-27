"""
form_generator.py — Generación de formularios dinámicos para NeuroMedIR.

Dos modos de generación:
    1. LLM-driven (preferido): El LLM genera preguntas como un médico real,
       específicas para los síntomas del paciente.
    2. Rule-based (fallback): Preguntas predefinidas basadas en keywords.

El modo LLM produce formularios mucho más relevantes porque:
    - Adapta las preguntas al cuadro clínico específico
    - Genera preguntas de diagnóstico diferencial que un médico real haría
    - No se limita a los síntomas predefinidos en código
"""

import re
import json
import string
import logging
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


_FORM_TEXT = {
    "es": {
        "title": "Evaluación Pre-diagnóstica",
        "description": (
            "Por favor revise y complete todos los campos a continuación para ayudarnos a "
            "entender mejor su caso y ofrecerle una búsqueda más precisa."
        ),
        "intensity_label": "Del 1 al 10, ¿Qué intensidad tiene su molestia principal?",
        "duration_label": "¿Hace cuánto tiempo comenzó con estos problemas?",
        "duration_options": ["Menos de 24 horas", "Unos pocos días", "Semanas", "Meses", "Años"],
        "dynamic_label": "Basado en casos similares, ¿Presenta usted también alguna de las siguientes condiciones o síntomas?",
        "dynamic_hint": "Marque todos los que apliquen.",
        "additional_label": "¿Algún otro detalle, condición pre-existente o medicamento que esté tomando?",
        "additional_placeholder": "Ej. Soy diabético, tomo Losartán...",
        "onset_label": "¿Cómo comenzó el síntoma principal?",
        "onset_options": ["De forma súbita", "De forma gradual", "No estoy seguro"],
        "fever_temp_label": "¿Cuál ha sido la temperatura más alta registrada?",
        "fever_temp_options": ["Menos de 38°C", "38–39°C", "39–40°C", "Más de 40°C", "No lo sé"],
        "fever_chills_label": "¿Ha tenido escalofríos?",
        "yes_no": ["Sí", "No"],
        "cough_type_label": "¿Cómo describiría la tos?",
        "cough_type_options": ["Seca", "Productiva", "No estoy seguro"],
        "cough_sputum_label": "Si es productiva, ¿cómo es la flema?",
        "cough_sputum_options": ["Transparente", "Amarilla/Verde", "Con sangre", "No aplica"],
        "headache_location_label": "¿Dónde se localiza principalmente el dolor de cabeza?",
        "headache_location_options": ["Frontal", "Temporal", "Occipital", "Generalizado", "No estoy seguro"],
        "headache_nausea_label": "¿Se acompaña de náuseas o vómitos?",
        "gi_frequency_label": "¿Con qué frecuencia ocurre?",
        "gi_frequency_options": ["1-2 veces/día", "3-5 veces/día", "Más de 5 veces/día", "No estoy seguro"],
        "dizziness_trigger_label": "¿Cuándo se presenta el mareo?",
        "dizziness_trigger_options": ["Al levantarme", "Al mover la cabeza", "Constante", "No estoy seguro"],
        "chest_trigger_label": "¿Cuándo aparece el dolor/opresión?",
        "chest_trigger_options": ["En reposo", "Con esfuerzo", "Al respirar", "No estoy seguro"],
        "chest_radiation_label": "¿Irradia hacia alguna zona?",
        "chest_radiation_options": ["Brazo", "Mandíbula", "Espalda", "No", "No estoy seguro"],
    },
    "en": {
        "title": "Pre-diagnostic Assessment",
        "description": (
            "Please review and complete all fields below to help us understand your case and "
            "provide a more accurate analysis."
        ),
        "intensity_label": "From 1 to 10, how intense is your main symptom?",
        "duration_label": "How long have you had these symptoms?",
        "duration_options": ["Less than 24 hours", "A few days", "Weeks", "Months", "Years"],
        "dynamic_label": "Based on similar cases, do you also experience any of the following?",
        "dynamic_hint": "Select all that apply.",
        "additional_label": "Any other detail, pre-existing condition, or medication?",
        "additional_placeholder": "E.g., I have diabetes, I take Losartan...",
        "onset_label": "How did the main symptom start?",
        "onset_options": ["Sudden", "Gradual", "Not sure"],
        "fever_temp_label": "What has been the highest recorded temperature?",
        "fever_temp_options": ["Below 38°C", "38–39°C", "39–40°C", "Above 40°C", "Not sure"],
        "fever_chills_label": "Have you had chills?",
        "yes_no": ["Yes", "No"],
        "cough_type_label": "How would you describe the cough?",
        "cough_type_options": ["Dry", "Productive", "Not sure"],
        "cough_sputum_label": "If productive, what is the sputum like?",
        "cough_sputum_options": ["Clear", "Yellow/Green", "Bloody", "Not applicable"],
        "headache_location_label": "Where is the headache mainly located?",
        "headache_location_options": ["Frontal", "Temporal", "Occipital", "Generalized", "Not sure"],
        "headache_nausea_label": "Is it accompanied by nausea or vomiting?",
        "gi_frequency_label": "How often does it occur?",
        "gi_frequency_options": ["1-2 times/day", "3-5 times/day", "More than 5 times/day", "Not sure"],
        "dizziness_trigger_label": "When does the dizziness happen?",
        "dizziness_trigger_options": ["When standing up", "When moving the head", "Constant", "Not sure"],
        "chest_trigger_label": "When does the pain/pressure appear?",
        "chest_trigger_options": ["At rest", "With exertion", "When breathing", "Not sure"],
        "chest_radiation_label": "Does it radiate to any area?",
        "chest_radiation_options": ["Arm", "Jaw", "Back", "No", "Not sure"],
    },
}


def _normalize_lang(lang: str) -> str:
    return "es" if lang not in ("es", "en") else lang


def _append_field(fields: list, used_ids: set, field: dict) -> None:
    field_id = field.get("id")
    if not field_id or field_id in used_ids:
        return
    fields.append(field)
    used_ids.add(field_id)


def sanitize_text(text: str) -> str:
    return text.translate(str.maketrans('', '', string.punctuation))


def fix_mojibake(text: str) -> str:
    if not text:
        return ""
    if "Ã" in text or "Â" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text
    return text


def normalize_candidate_term(term: str) -> str:
    if not term:
        return ""
    if "�" in term:
        return ""
    term = fix_mojibake(term)
    term = sanitize_text(term)
    term = re.sub(r"\s+", " ", term).strip().lower()
    if len(term) < 4:
        return ""
    if re.fullmatch(r"[a-z]{1,2}", term):
        return ""
    if "â" in term or "ã" in term:
        return ""
    if "ntomas" in term and not term.startswith("s"):
        return ""
    return term


def extract_form_symptoms_prf(query: str, retrieved_docs: list, top_n: int = 10) -> list:
    """
    Pseudo-Relevance Feedback (PRF) usando TF-IDF.
    Extrae términos médicos de los documentos recuperados.
    """
    if not retrieved_docs:
        return []

    # Stopwords ampliadas para filtrar fuentes y términos no médicos
    stop_words = [
        "el", "la", "los", "las", "un", "una", "de", "del", "al", "en", "para",
        "por", "con", "sin", "su", "sus", "como", "esta", "esto", "este", "es", "son",
        "paciente", "estudio", "caso", "the", "and", "of", "to", "in", "for", "with",
        "on", "is", "was", "also", "may", "can", "more", "information", "page",
        # Fuentes y sitios web — crítico filtrar estos
        "medlineplus", "medline", "plus", "nhs", "pubmed", "scielo", "ncbi",
        "español", "espanol", "english", "spanish", "medlineplus español",
        "medlineplus espanol", "nhs uk", "britanico", "britannica",
        # Términos estructurales de documentos médicos
        "introduccion", "introduction", "summary", "resumen", "basics",
        "diagnosis", "diagnostico", "treatment", "tratamiento", "overview",
        "start", "here", "learn", "more", "see", "also", "called", "nombres",
        "otros", "other", "names", "pagina", "page", "basics", "tests",
        "prevention", "factors", "therapies", "terapias", "related", "issues",
        "living", "clinical", "trials", "research", "referencias", "referencias",
        "also called", "on this", "this page",
    ]

    vectorizer = TfidfVectorizer(
        stop_words=stop_words,
        ngram_range=(1, 2),
        max_features=200,
        lowercase=True,
        token_pattern=r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{4,}\b',
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(retrieved_docs)
    except ValueError:
        return []

    sum_tfidf = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
    feature_names = vectorizer.get_feature_names_out()

    query_terms = set(sanitize_text(query.lower()).split())

    # Lista de términos médicos válidos para filtrar
    MEDICAL_TERMS_ES = {
        "dolor", "fiebre", "tos", "nausea", "nauseas", "mareo", "vertigo",
        "cansancio", "fatiga", "diarrea", "vomito", "vomitos", "congestion",
        "inflamacion", "hinchazón", "hinchaz", "sangrado", "hemorragia",
        "picazon", "ardor", "escalofrío", "escalofríos", "perdida", "debilidad",
        "palpitaciones", "disnea", "edema", "erupciones", "sarpullido",
        "temblores", "convulsiones", "desmayo", "sincope", "presion", "tension",
        "glucosa", "azucar", "colesterol", "infeccion", "bacteria", "virus",
        "alergia", "asma", "diabetes", "hipertension", "anemia", "artritis",
        "migraña", "migrana", "cefalea", "bronquitis", "neumonia", "gripe",
        "resfriado", "sinusitis", "otitis", "gastritis", "colitis", "hepatitis",
        "insuficiencia", "arritmia", "taquicardia", "bradicardia",
    }
    MEDICAL_TERMS_EN = {
        "pain", "fever", "cough", "nausea", "dizziness", "fatigue", "diarrhea",
        "vomiting", "inflammation", "swelling", "bleeding", "hemorrhage",
        "itching", "burning", "chills", "weakness", "palpitations", "dyspnea",
        "edema", "rash", "tremors", "seizures", "fainting", "syncope",
        "pressure", "glucose", "sugar", "cholesterol", "infection", "bacteria",
        "virus", "allergy", "asthma", "diabetes", "hypertension", "anemia",
        "arthritis", "migraine", "headache", "bronchitis", "pneumonia",
        "influenza", "cold", "sinusitis", "otitis", "gastritis", "colitis",
        "hepatitis", "insufficiency", "arrhythmia", "tachycardia",
    }
    VALID_MEDICAL = MEDICAL_TERMS_ES | MEDICAL_TERMS_EN

    # Patrones a excluir explícitamente
    EXCLUDE_PATTERNS = re.compile(
        r'(medline|medplus|pubmed|scielo|ncbi|nhs|español|espanol|english|'
        r'introduction|summary|basics|diagnosis|treatment|overview|'
        r'called|page|learn|more|also|names|tests|prevention|therapies|'
        r'living|trials|research|related|issues)',
        re.IGNORECASE
    )

    word_scores = []
    for word, score in zip(feature_names, sum_tfidf):
        word_clean = normalize_candidate_term(word)
        if not word_clean:
            continue
        # Excluir si contiene patrones de fuentes/estructura
        if EXCLUDE_PATTERNS.search(word_clean):
            continue
        # Solo incluir si es término médico conocido O no está en query
        if any(q_term in word_clean for q_term in query_terms):
            continue
        # Preferir términos médicos conocidos, pero incluir otros si son relevantes
        is_medical = any(med in word_clean for med in VALID_MEDICAL)
        if is_medical or (len(word_clean) >= 5 and score > 0.1):
            word_scores.append((word_clean, score, is_medical))

    # Ordenar: primero los términos médicos conocidos, luego por score
    word_scores.sort(key=lambda x: (not x[2], -x[1]))
    top_terms = [word for word, score, _ in word_scores[:top_n]]
    return list(dict.fromkeys(top_terms))

# =========================================================================
# LLM-DRIVEN FORM GENERATION (primary method)
# =========================================================================

def generate_llm_form_schema(
    query: str,
    detected_symptoms: list,
    llm_client,
    lang: str = "es",
) -> Optional[dict]:
    """
    Genera el esquema del formulario usando el LLM.

    El LLM actúa como un médico que decide qué preguntas hacerle al paciente
    en función de sus síntomas específicos. Esto produce formularios mucho más
    relevantes y adaptados que el enfoque rule-based.

    Args:
        query: Mensaje del paciente.
        detected_symptoms: Síntomas detectados por el intent classifier.
        llm_client: Cliente LLM con método chat().
        lang: Código de idioma.

    Returns:
        Esquema del formulario como dict, o None si falla.
    """
    if llm_client is None or not llm_client.is_available:
        return None

    is_spanish = lang == "es"

    if is_spanish:
        system_prompt = (
            "Eres un médico especialista. Un paciente te describe sus síntomas. "
            "Tu tarea es generar las preguntas específicas que le harías para "
            "llegar a un diagnóstico diferencial preciso. "
            "Las preguntas deben ser CLARAS, FÁCILES de responder para cualquier persona "
            "de cualquier edad, y orientadas a distinguir entre posibles condiciones. "
            "DEBES responder SOLO con un objeto JSON válido, sin texto adicional.\n\n"
            "El JSON debe tener esta estructura exacta:\n"
            '{\n'
            '  "fields": [\n'
            '    {\n'
            '      "id": "identificador_unico",\n'
            '      "type": "select|multiselect_checkbox|slider|textarea",\n'
            '      "label": "Pregunta para el paciente",\n'
            '      "options": ["Opción 1", "Opción 2"],\n'
            '      "min": 1,\n'
            '      "max": 10,\n'
            '      "required": true,\n'
            '      "hint": "Texto de ayuda opcional"\n'
            '    }\n'
            '  ]\n'
            '}\n\n'
            'Reglas:\n'
            '- "select": pregunta con opciones excluyentes (radio buttons)\n'
            '- "multiselect_checkbox": pregunta con opciones múltiples (checkboxes)\n'
            '- "slider": escala numérica (requiere min y max)\n'
            '- "textarea": texto libre\n'
            '- Genera entre 4 y 8 preguntas relevantes\n'
            '- NO generes preguntas sobre intensidad ni duración (se agregan automáticamente)\n'
            '- Cada "id" debe ser único, en snake_case, sin espacios\n'
            '- Los "label" deben ser preguntas claras en español\n'
            '- Las "options" deben ser comprensibles para cualquier persona\n'
            '- Incluye siempre "No estoy seguro" como opción en preguntas de selección\n'
        )

        user_message = (
            f"El paciente dice: \"{query}\"\n\n"
            f"Síntomas detectados: {', '.join(detected_symptoms) if detected_symptoms else 'No se detectaron síntomas específicos'}\n\n"
            "Genera las preguntas que le harías a este paciente como médico. "
            "Responde SOLO con el JSON."
        )
    else:
        system_prompt = (
            "You are a specialist doctor. A patient describes their symptoms. "
            "Your task is to generate the specific questions you would ask them to "
            "arrive at a precise differential diagnosis. "
            "Questions must be CLEAR, EASY to answer for any person of any age, "
            "and oriented toward distinguishing between possible conditions. "
            "You MUST respond ONLY with a valid JSON object, no additional text.\n\n"
            "The JSON must have this exact structure:\n"
            '{\n'
            '  "fields": [\n'
            '    {\n'
            '      "id": "unique_identifier",\n'
            '      "type": "select|multiselect_checkbox|slider|textarea",\n'
            '      "label": "Question for the patient",\n'
            '      "options": ["Option 1", "Option 2"],\n'
            '      "min": 1,\n'
            '      "max": 10,\n'
            '      "required": true,\n'
            '      "hint": "Optional help text"\n'
            '    }\n'
            '  ]\n'
            '}\n\n'
            'Rules:\n'
            '- "select": exclusive options (radio buttons)\n'
            '- "multiselect_checkbox": multiple options (checkboxes)\n'
            '- "slider": numeric scale (requires min and max)\n'
            '- "textarea": free text\n'
            '- Generate between 4 and 8 relevant questions\n'
            '- Do NOT generate questions about intensity or duration (added automatically)\n'
            '- Each "id" must be unique, in snake_case, no spaces\n'
            '- "label" must be clear questions in English\n'
            '- "options" must be understandable for any person\n'
            '- Always include "Not sure" as an option in selection questions\n'
        )

        user_message = (
            f"The patient says: \"{query}\"\n\n"
            f"Detected symptoms: {', '.join(detected_symptoms) if detected_symptoms else 'No specific symptoms detected'}\n\n"
            "Generate the questions you would ask this patient as a doctor. "
            "Respond ONLY with the JSON."
        )

    try:
        response = llm_client.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            max_new_tokens=2048,
            json_mode=True,
        )

        if not response:
            logger.warning("LLM form generation: empty response.")
            return None

        # Parsear JSON
        schema_data = json.loads(response)

        if "fields" not in schema_data or not isinstance(schema_data["fields"], list):
            logger.warning("LLM form generation: invalid schema structure.")
            return None

        # Validar y limpiar cada campo
        valid_fields = []
        used_ids = set()
        for field in schema_data["fields"]:
            if not isinstance(field, dict):
                continue
            field_id = field.get("id", "")
            field_type = field.get("type", "")
            field_label = field.get("label", "")

            if not field_id or not field_type or not field_label:
                continue
            if field_id in used_ids:
                continue
            if field_type not in ("select", "multiselect_checkbox", "slider", "textarea"):
                continue

            clean_field = {
                "id": field_id,
                "type": field_type,
                "label": field_label,
                "required": bool(field.get("required", False)),
            }

            if field_type in ("select", "multiselect_checkbox"):
                options = field.get("options", [])
                if isinstance(options, list) and len(options) > 0:
                    clean_field["options"] = [str(o) for o in options]
                else:
                    continue

            if field_type == "slider":
                clean_field["min"] = int(field.get("min", 1))
                clean_field["max"] = int(field.get("max", 10))

            if field.get("hint"):
                clean_field["hint"] = str(field["hint"])

            if field.get("placeholder"):
                clean_field["placeholder"] = str(field["placeholder"])

            valid_fields.append(clean_field)
            used_ids.add(field_id)

        if not valid_fields:
            logger.warning("LLM form generation: no valid fields after parsing.")
            return None

        # Construir esquema final con campos estándar + campos LLM
        lang_key = _normalize_lang(lang)
        text = _FORM_TEXT[lang_key]

        final_fields = []
        final_used_ids = set()

        # Campos estándar obligatorios
        _append_field(final_fields, final_used_ids, {
            "id": "intensity",
            "type": "slider",
            "label": text["intensity_label"],
            "min": 1,
            "max": 10,
            "required": True,
        })

        _append_field(final_fields, final_used_ids, {
            "id": "duration",
            "type": "select",
            "label": text["duration_label"],
            "options": text["duration_options"],
            "required": True,
        })

        # Campos generados por el LLM
        for field in valid_fields:
            if field["id"] not in ("intensity", "duration", "additional_notes", "dynamic_symptoms"):
                _append_field(final_fields, final_used_ids, field)

        # Campo final de notas
        _append_field(final_fields, final_used_ids, {
            "id": "additional_notes",
            "type": "textarea",
            "label": text["additional_label"],
            "placeholder": text["additional_placeholder"],
            "required": False,
        })

        return {
            "title": text["title"],
            "description": text["description"],
            "original_query": query,
            "fields": final_fields,
        }

    except json.JSONDecodeError as e:
        logger.error(f"LLM form generation: JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM form generation failed: {e}")
        return None


# =========================================================================
# RULE-BASED FORM GENERATION (fallback when LLM is unavailable)
# =========================================================================

def generate_dynamic_form_schema(
    query: str,
    extracted_symptoms: list,
    detected_symptoms: list = None,
    lang: str = "es",
) -> dict:
    """
    Genera el esquema del formulario usando reglas (fallback).

    Se usa cuando el LLM no está disponible.
    """
    lang = _normalize_lang(lang)
    text = _FORM_TEXT[lang]

    detected_symptoms = detected_symptoms or []
    combined_text = " ".join(extracted_symptoms + detected_symptoms).lower()

    fields: list = []
    used_ids: set = set()

    _append_field(fields, used_ids, {
        "id": "intensity",
        "type": "slider",
        "label": text["intensity_label"],
        "min": 1,
        "max": 10,
        "required": True,
    })

    _append_field(fields, used_ids, {
        "id": "duration",
        "type": "select",
        "label": text["duration_label"],
        "options": text["duration_options"],
        "required": True,
    })

    if combined_text.strip():
        _append_field(fields, used_ids, {
            "id": "onset",
            "type": "select",
            "label": text["onset_label"],
            "options": text["onset_options"],
            "required": False,
        })

    def has_any(*keywords):
        return any(k in combined_text for k in keywords)

    if has_any("fiebre", "fever"):
        _append_field(fields, used_ids, {
            "id": "fever_temperature",
            "type": "select",
            "label": text["fever_temp_label"],
            "options": text["fever_temp_options"],
            "required": False,
        })
        _append_field(fields, used_ids, {
            "id": "fever_chills",
            "type": "select",
            "label": text["fever_chills_label"],
            "options": text["yes_no"],
            "required": False,
        })

    if has_any("tos", "cough"):
        _append_field(fields, used_ids, {
            "id": "cough_type",
            "type": "select",
            "label": text["cough_type_label"],
            "options": text["cough_type_options"],
            "required": False,
        })
        _append_field(fields, used_ids, {
            "id": "cough_sputum",
            "type": "select",
            "label": text["cough_sputum_label"],
            "options": text["cough_sputum_options"],
            "required": False,
        })

    if has_any("dolor de cabeza", "headache"):
        _append_field(fields, used_ids, {
            "id": "headache_location",
            "type": "select",
            "label": text["headache_location_label"],
            "options": text["headache_location_options"],
            "required": False,
        })
        _append_field(fields, used_ids, {
            "id": "headache_nausea",
            "type": "select",
            "label": text["headache_nausea_label"],
            "options": text["yes_no"],
            "required": False,
        })

    if has_any("nausea", "nauseas", "vomito", "vomiting", "diarrea", "diarrhea"):
        _append_field(fields, used_ids, {
            "id": "gi_frequency",
            "type": "select",
            "label": text["gi_frequency_label"],
            "options": text["gi_frequency_options"],
            "required": False,
        })

    if has_any("mareo", "vertigo", "dizziness"):
        _append_field(fields, used_ids, {
            "id": "dizziness_trigger",
            "type": "select",
            "label": text["dizziness_trigger_label"],
            "options": text["dizziness_trigger_options"],
            "required": False,
        })

    if has_any("dolor de pecho", "opresion en el pecho", "chest pain", "chest pressure"):
        _append_field(fields, used_ids, {
            "id": "chest_trigger",
            "type": "select",
            "label": text["chest_trigger_label"],
            "options": text["chest_trigger_options"],
            "required": False,
        })
        _append_field(fields, used_ids, {
            "id": "chest_radiation",
            "type": "select",
            "label": text["chest_radiation_label"],
            "options": text["chest_radiation_options"],
            "required": False,
        })

    schema = {
        "title": text["title"],
        "description": text["description"],
        "original_query": query,
        "fields": fields,
    }

    if extracted_symptoms:
        formatted_options = [fix_mojibake(sym).capitalize() for sym in extracted_symptoms]
        _append_field(schema["fields"], used_ids, {
            "id": "dynamic_symptoms",
            "type": "multiselect_checkbox",
            "label": text["dynamic_label"],
            "options": formatted_options,
            "required": False,
            "hint": text["dynamic_hint"],
        })

    _append_field(schema["fields"], used_ids, {
        "id": "additional_notes",
        "type": "textarea",
        "label": text["additional_label"],
        "placeholder": text["additional_placeholder"],
        "required": False,
    })

    return schema