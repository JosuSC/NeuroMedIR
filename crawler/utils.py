import hashlib
import logging
import re
from urllib.parse import urlparse, urlunparse


"""
utils.py — Funciones pequeñas de apoyo para el crawler.

Son helpers muy simples, pero son importantes porque mantienen el resto
del código más limpio: logging, normalización de URLs, limpieza de texto
e identificación de duplicados.
"""


def setup_logger(name: str) -> logging.Logger:
    """Crea un logger consistente para todo el paquete crawler."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


from urllib.parse import (
    urlparse,
    urlunparse,
    parse_qsl,
    urlencode,
)

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def normalize_url(url: str) -> str:
    """
    Normaliza una URL para evitar duplicados semánticos.

    Acciones:
        - lowercase de scheme y host
        - elimina fragmentos (#section)
        - elimina trailing slash redundante
        - elimina parámetros tracking/analytics
        - ordena query params para canonicalización estable
    """
    parsed = urlparse(url.strip())

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    netloc = netloc.replace(":80", "").replace(":443", "")

    # Normalizar path
    path = parsed.path.rstrip("/") if parsed.path not in ("", "/") else "/"

    # Parsear query params
    query_params = parse_qsl(parsed.query, keep_blank_values=False)

    # Filtrar tracking params
    filtered_params = [
        (k, v)
        for k, v in query_params
        if k.lower() not in TRACKING_PARAMS
    ]

    # Orden estable para evitar duplicados por orden distinto
    filtered_params.sort()

    # Reconstruir query
    query = urlencode(filtered_params, doseq=True)

    # Eliminar fragment (#...)
    fragment = ""

    return urlunparse((scheme, netloc, path, "", query, fragment))


def is_http_url(url: str) -> bool:
    """Comprueba si el string parece ser una URL HTTP/HTTPS válida."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def domain_from_url(url: str) -> str:
    """Extrae el host principal de una URL."""
    return (urlparse(url).hostname or "").lower()


def same_domain_or_subdomain(url: str, domain: str) -> bool:
    """Verifica si una URL pertenece al dominio dado o a uno de sus subdominios."""
    host = domain_from_url(url)
    if not host:
        return False
    return host == domain or host.endswith(f".{domain}")


def strip_noise(text: str) -> str:
    """Limpia espacios repetidos y deja el texto más legible."""
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def text_fingerprint(text: str) -> str:
    """Genera una huella corta para detectar contenido duplicado."""
    normalized = re.sub(r"\W+", " ", (text or "").lower()).strip()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()
