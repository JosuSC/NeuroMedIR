from collections import Counter
from urllib.parse import urlparse


EN_MARKERS = {
    "the", "and", "with", "for", "from", "health", "disease", "treatment", "patient", "study",
}
ES_MARKERS = {
    "el", "la", "los", "las", "con", "para", "salud", "enfermedad", "tratamiento", "paciente",
}


def detect_language(text: str, hint: str = "") -> str:
    if hint in {"en", "es"}:
        return hint

    tokens = [t.lower() for t in (text or "").split() if len(t) > 1]
    if not tokens:
        return "unknown"

    counts = Counter(tokens)
    en_score = sum(counts[t] for t in EN_MARKERS)
    es_score = sum(counts[t] for t in ES_MARKERS)

    if en_score == es_score == 0:
        return "unknown"
    return "en" if en_score >= es_score else "es"


def infer_language_from_url(url: str) -> str:
    lowered = (url or "").lower()
    path = urlparse(lowered).path
    if "/es/" in path or "/spanish/" in path or "lang=es" in lowered:
        return "es"
    return "en"
