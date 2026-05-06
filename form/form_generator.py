import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import string

def sanitize_text(text: str) -> str:
    """Elimina signos de puntuación básicos."""
    return text.translate(str.maketrans('', '', string.punctuation))

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
        word_clean = sanitize_text(word)
        # Filtros heurísticos: Evitar términos muy cortos (basura)
        if len(word_clean) < 4:
            continue
            
        # Si ninguna palabra del síntoma coincide trivialmente con lo que originó la búsqueda:
        if not any(q_term in word_clean for q_term in query_terms):
            word_scores.append((word, score))
            
    # 5. Ordenar decrecientemente por relevancia PRF total
    word_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 6. Retornar los top N limpios
    return [word for word, score in word_scores[:top_n]]

def generate_dynamic_form_schema(query: str, extracted_symptoms: list[str]) -> dict:
    """
    Genera el esquema JSON necesario para renderizar un formulario profesional y validado
    en la interfaz de frontend. Todos los campos están marcados con reglas de negocio.
    """
    # Campos estándar médicos requeridos
    schema = {
        "title": "Evaluación Pre-diagnóstica",
        "description": "Por favor revise y complete todos los campos a continuación para ayudarnos a entender mejor su caso y ofrecerle una búsqueda más precisa. Tendrá oportunidad de revisarlo antes de enviarlo.",
        "original_query": query,
        "fields": [
            {
                "id": "intensity",
                "type": "slider",
                "label": "Del 1 al 10, ¿Qué intensidad tiene su molestia principal?",
                "min": 1,
                "max": 10,
                "required": True
            },
            {
                "id": "duration",
                "type": "select",
                "label": "¿Hace cuánto tiempo comenzó con estos problemas?",
                "options": ["Menos de 24 horas", "Unos pocos días", "Semanas", "Meses", "Años"],
                "required": True
            }
        ]
    }
    
    # Si logramos extraer conocimiento dinámico del motor de SRI
    if extracted_symptoms:
        # Capitalizamos la primera letra de cada término para que se vea más natural en la UI
        formatted_options = [sym.capitalize() for sym in extracted_symptoms]
        schema["fields"].append({
            "id": "dynamic_symptoms",
            "type": "multiselect_checkbox",
            "label": "Basado en casos similares, ¿Presenta usted también alguna de las siguientes condiciones o síntomas?",
            "options": formatted_options,
            "required": False,  # Se deja false porque el paciente puede no tener ninguno de estos
            "hint": "Marque todos los que apliquen."
        })
        
    # Campo final estándar para requerimientos adicionales (anamnesis)
    schema["fields"].append({
        "id": "additional_notes",
        "type": "textarea",
        "label": "¿Algún otro detalle, condición pre-existente o medicamento que esté tomando?",
        "placeholder": "Ej. Soy diabético, tomo Losartán...",
        "required": False
    })
    
    return schema
