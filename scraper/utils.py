"""
utils.py — Funciones de apoyo para el módulo scraper.

Responsabilidades:
    - Limpieza de texto (espacios, ruido, normalización)
    - Configuración consistente de logging
    - Huellas digitales para detección de duplicados.
"""

import hashlib
import logging
import re


def setup_logger(nombre: str) -> logging.Logger:
    """Crea un logger consistente para todo el paquete scraper.

    Evita duplicar handlers si se llama múltiples veces.
    Retorna el logger listo para usar con formato estándar.

    Args:
        nombre: Identificador del logger (usualmente __name__).

    Returns:
        Logger configurado con handler y formato estándar.
    """
    logger = logging.getLogger(nombre)
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


def strip_noise(texto: str) -> str:
    """Elimina espacios repetidos y deja el texto más legible.

    Reemplaza secuencias de whitespace (espacios, tabs, saltos de línea)
    por un solo espacio, y recorta extremos.

    Args:
        texto: Texto crudo con posibles espacios repetidos.

    Returns:
        Texto limpio con espacios simples.
    """
    return re.sub(r"\s+", " ", texto or "").strip()


def clean_text(texto: str) -> str:
    """Limpia texto: elimina espacios repetidos y normaliza extremos.

    Similar a strip_noise pero con verificación de entrada None/vacío.
    Se usa como paso de normalización antes de almacenar contenido.

    Args:
        texto: Texto crudo a limpiar.

    Returns:
        Texto normalizado, o cadena vacía si la entrada es None/vacía.
    """
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def text_fingerprint(texto: str) -> str:
    """Genera una huella digital SHA-1 para detectar contenido duplicado.

    Normaliza el texto (minúsculas, solo alfanuméricos) y calcula
    el hash SHA-1. Dos textos con el mismo contenido producen la
    misma huella, independientemente de formato o mayúsculas.

    Complejidad: O(n) donde n = longitud del texto.

    Args:
        texto: Texto a hashear.

    Returns:
        String hexadecimal de 40 caracteres (SHA-1).
    """
    normalizado = re.sub(r"\W+", " ", (texto or "").lower()).strip()
    return hashlib.sha1(normalizado.encode("utf-8")).hexdigest()

