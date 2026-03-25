import logging
from typing import Optional
import re
from urllib.parse import urlparse

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

def clean_text(text: str) -> str:
    """Elimina espacios adicionales y normaliza el texto."""
    if not text:
        return ""
    # Reemplaza múltiples espacios, tabulaciones y saltos de línea por un solo espacio
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
