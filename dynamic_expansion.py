"""
dynamic_expansion.py — Expansión dinámica del corpus para NeuroMedIR.

Se activa cuando el corpus local (principal + expansión) es insuficiente.
Crawling ligero y enfocado sobre 2 fuentes médicas confiables en español,
garantizando 1-2 resultados acordes a la consulta.
"""

import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus

from crawler.config import CrawlConfig, DomainConfig
from crawler.crawler import CorpusCrawler
from indexing.configs import settings as idx_settings

logger = logging.getLogger(__name__)


def _build_dynamic_domains(url_query: str) -> List[DomainConfig]:
    """Dos fuentes en español con búsqueda por query."""
    return [
        DomainConfig(
            domain="medlineplus.gov",
            seeds=[
                f"https://medlineplus.gov/spanish/search/?query={url_query}",
            ],
            language_hint="es",
            source_name="MedlinePlus ES (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["medlineplus.gov"],
        ),
        DomainConfig(
            domain="msdmanuals.com",
            seeds=[
                f"https://www.msdmanuals.com/es/hogar/searchresults?query={url_query}",
            ],
            language_hint="es",
            source_name="MSD Manuals ES (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["msdmanuals.com"],
        ),
    ]


def expand_corpus_from_query(
    query: str,
    max_new_docs: int = 2,
    start_doc_id: Optional[int] = None,
) -> List[Dict]:
    """
    Expande el corpus dinámicamente usando la consulta del usuario.

    Args:
        query: Consulta que disparó la expansión.
        max_new_docs: Número de documentos nuevos objetivo (1-2 basta).
        start_doc_id: id inicial para los docs nuevos (evita colisión con
                      el corpus principal y la expansión previa). Si es None,
                      el crawler usa su lógica por defecto.

    Returns:
        Lista de documentos nuevos (vacía si falla el crawling).
    """
    logger.info(f"Expansión dinámica iniciada para: '{query}'")

    url_query = quote_plus(query.lower().strip())
    all_domains = _build_dynamic_domains(url_query)

    config = CrawlConfig()
    config.max_pages = 40          # margen para encontrar páginas con contenido
    config.max_depth = 2           # seguir 1 nivel desde resultados de búsqueda
    config.delay_seconds = 0.3
    config.min_content_chars = 300 # umbral más permisivo para garantizar hits
    config.min_valid_documents = max_new_docs
    config.language_targets = {"es": max_new_docs}  # solo español
    config.relaxed_quality = True  # gate relajado: omite heurísticas frágiles
    # output_dir = data/expansion/ (el padre de processed/) para que el storage
    # cree processed/raw/rejected al nivel correcto, sin anidar.
    config.output_dir = idx_settings.EXPANSION_DATA_DIR.parent

    try:
        crawler = CorpusCrawler(
            config=config,
            domains=all_domains,
            scraper=None,
        )
        # Sembrar el contador de id para no colisionar con corpus/expansión.
        if start_doc_id is not None:
            crawler.next_doc_id = start_doc_id

        crawler.run()

        new_docs = crawler.valid_docs
        logger.info(
            f"Expansión completada: {len(new_docs)} documentos nuevos en español"
        )
        return new_docs

    except Exception as e:
        logger.error(f"Expansión dinámica falló: {e}")
        return []