import re
import string

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


_FORM_TEXT = {
    "es": {
        "title": "Evaluación Pre-diagnóstica",
        "description": (
            "Por favor revise y complete todos los campos a continuación para ayudarnos a "
            "entender mejor su caso y ofrecerle una búsqueda más precisa. Tendrá oportunidad "
            "de revisarlo antes de enviarlo."
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
            "provide a more accurate analysis. You will be able to review it before submitting."
        ),
        "intensity_label": "From 1 to 10, how intense is your main symptom?",
        "duration_label": "How long have you had these symptoms?",
        "duration_options": ["Less than 24 hours", "A few days", "Weeks", "Months", "Years"],
        "dynamic_label": "Based on similar cases, do you also experience any of the following conditions or symptoms?",
        "dynamic_hint": "Select all that apply.",
        "additional_label": "Any other detail, pre-existing condition, or medication you are taking?",
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
    """Elimina signos de puntuación básicos."""
    return text.translate(str.maketrans('', '', string.punctuation))


def fix_mojibake(text: str) -> str:
    """Intenta corregir texto mojibake típico (ej. espaÃ±ol -> español)."""
    if not text:
        return ""

    # Heurística: solo intentar recodificar cuando hay patrones sospechosos.
    if "Ã" in text or "Â" in text:
        try:
            repaired = text.encode("latin1").decode("utf-8")
            return repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text
    return text


def normalize_candidate_term(term: str) -> str:
    """Limpia términos candidatos para evitar basura visual en el formulario."""
    if not term:
        return ""

    # Si ya hay caracteres de reemplazo (U+FFFD), ese texto está corrupto.
    # Lo descartamos para no mostrar opciones rotas como "espa�ol".
    if "�" in term:
        return ""

    term = fix_mojibake(term)
    term = sanitize_text(term)
    term = re.sub(r"\s+", " ", term).strip().lower()

    # Quitar tokens muy cortos o claramente rotos.
    if len(term) < 4:
        return ""
    if re.fullmatch(r"[a-z]{1,2}", term):
        return ""
    if "â" in term or "ã" in term:
        return ""
    if "ntomas" in term and not term.startswith("s"):
        return ""

    return term

def extract_form_symptoms_prf(query: str, retrieved_docs: list[str], top_n: int = 10) -> list[str]:
    """
    Algoritmo: Pseudo-Relevance Feedback (PRF) usando TF-IDF.
    Analiza la colección local de N mejores documentos devueltos por el motor
    para extraer términos (enfermedades/síntomas probabilísticos) que no están 
    en la query original.
    """
    if not retrieved_docs:
        return []
        
    # 1. Pipeline de extracción: Solo nos interesan las palabras más representativas.
    # Excluimos stop_words genéricas. Extraemos bi-gramas y unigramas.
    # Usamos español e inglés ya que la base puede ser multilingüe.
    stop_words = ["el", "la", "los", "las", "un", "una", "de", "del", "al", "en", "para",
                  "por", "con", "sin", "su", "sus", "como", "esta", "esto", "este", "es", "son",
                  "paciente", "estudio", "caso", "the", "and", "of", "to", "in", "for", "with", "on", "is", "was"]
                  
    vectorizer = TfidfVectorizer(
        stop_words=stop_words,
        ngram_range=(1, 2),
        max_features=200, 
        lowercase=True
    )
    
    # 2. Computar matriz TF-IDF sobre el espacio vectorial top-K
    try:
        tfidf_matrix = vectorizer.fit_transform(retrieved_docs)
    except ValueError:
        # Fallback de seguridad si los documentos están vacíos o corruptos
        return []
        
    # 3. Sumarizar importancia global de cada característica (Término)
    sum_tfidf = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
    feature_names = vectorizer.get_feature_names_out()
    
    # 4. Excluir términos redundantes o que ya dijo el paciente
    query_terms = set(sanitize_text(query.lower()).split())
    word_scores = []
    
    for word, score in zip(feature_names, sum_tfidf):
        word_clean = normalize_candidate_term(word)

        # Filtros heurísticos: Evitar términos muy cortos (basura)
        if not word_clean:
            continue
            
        # Si ninguna palabra del síntoma coincide trivialmente con lo que originó la búsqueda:
        if not any(q_term in word_clean for q_term in query_terms):
            word_scores.append((word_clean, score))
            
    # 5. Ordenar decrecientemente por relevancia PRF total
    word_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 6. Retornar los top N limpios
    top_terms = [word for word, score in word_scores[:top_n]]
    return list(dict.fromkeys(top_terms))

def generate_dynamic_form_schema(
    query: str,
    extracted_symptoms: list[str],
    detected_symptoms: list[str] | None = None,
    lang: str = "es",
) -> dict:
    """
    Genera el esquema JSON necesario para renderizar un formulario profesional y validado
    en la interfaz de frontend. Todos los campos están marcados con reglas de negocio.
    """
    lang = _normalize_lang(lang)
    text = _FORM_TEXT[lang]

    detected_symptoms = detected_symptoms or []
    combined_text = " ".join(extracted_symptoms + detected_symptoms).lower()

    # Campos estándar médicos requeridos
    fields: list[dict] = []
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

    # Reglas de preguntas dinámicas basadas en síntomas
    def has_any(*keywords: str) -> bool:
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
    
    # Si logramos extraer conocimiento dinámico del motor de SRI
    if extracted_symptoms:
        # Capitalizamos la primera letra de cada término para que se vea más natural en la UI
        formatted_options = [fix_mojibake(sym).capitalize() for sym in extracted_symptoms]
        _append_field(schema["fields"], used_ids, {
            "id": "dynamic_symptoms",
            "type": "multiselect_checkbox",
            "label": text["dynamic_label"],
            "options": formatted_options,
            "required": False,
            "hint": text["dynamic_hint"],
        })
        
    # Campo final estándar para requerimientos adicionales (anamnesis)
    _append_field(schema["fields"], used_ids, {
        "id": "additional_notes",
        "type": "textarea",
        "label": text["additional_label"],
        "placeholder": text["additional_placeholder"],
        "required": False,
    })
    
    return schema
