import logging
from typing import Optional
import re
from urllib.parse import urlparse, urlunparse

def setup_logger(name: str) -> logging.Logger:
    """Configura y retorna un logger estandarizado."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def is_valid_url(url: str) -> bool:
    """Verifica sintácticamente si un string es una URL válida."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def normalize_url(url: str) -> str:
    """Normaliza URL para deduplicación básica (scheme/host/path)."""
    if not url:
        return ""

    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Evita tratar '/page' y '/page/' como páginas distintas.
    path = parsed.path.rstrip('/') if parsed.path != '/' else '/'

    return urlunparse((scheme, netloc, path, '', parsed.query, ''))

def clean_text(text: str) -> str:
    """Elimina espacios adicionales y normaliza el texto."""
    if not text:
        return ""
    # Reemplaza múltiples espacios, tabulaciones y saltos de línea por un solo espacio
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
