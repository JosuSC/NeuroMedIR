"""
scraper — Módulo de extracción de contenido web para NeuroMedIR.

Responsabilidades exclusivas de scraping:
    - Descargar páginas web con reintentos y backoff exponencial
    - Extraer contenido principal usando selectores CSS por dominio
    - Extraer enlaces absolutos desde HTML
    - Clasificar y validar documentos extraídos

"""

from .scraper import DomainScraper, DOMAIN_SELECTORS

from .utils import clean_text, strip_noise, setup_logger

__all__ = [
    "DomainScraper",
    "DOMAIN_SELECTORS",
    
    "clean_text",
    "strip_noise",
    "setup_logger",
]

