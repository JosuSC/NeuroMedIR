"""
crawler — Módulo de crawling BFS para NeuroMedIR.

Responsabilidades exclusivas de crawling:
    - Coordinar el flujo BFS de navegación web
    - Respetar robots.txt y políticas de delay
    - Gestionar la cola de URLs (semillas, profundidad, dominios)
    - Validar calidad de documentos
    - Persistir resultados en disco
    - Balancear el corpus por idioma

NOTA: El scraping (fetch HTTP, parsear HTML, extraer enlaces) se delega
al módulo scraper/. Este módulo NO contiene código de scraping.
Si necesitas hacer scraping sin crawling, usa scraper.DomainScraper directamente.
"""

from .config import CrawlConfig, DomainConfig, default_crawl_config
from .crawler import CorpusCrawler

__all__ = [
    "CrawlConfig",
    "DomainConfig",
    "default_crawl_config",
    "CorpusCrawler",
]