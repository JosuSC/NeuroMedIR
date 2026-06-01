"""
dynamic_expansion.py — Expansión dinámica del corpus para NeuroMedIR.

Estrategia: cuando el corpus local es insuficiente, se usa SerpApi (Google)
para obtener URLs reales de artículos en fuentes médicas confiables, y luego
se scrapean esas URLs directas (que sí tienen contenido, a diferencia de las
páginas de búsqueda con JS). Los documentos válidos se indexan en los índices
de expansión, separados del corpus principal.

Consumo de SerpApi: 1 búsqueda por expansión (plan free = 250/mes).
"""

import os
import logging
from typing import List, Dict, Optional

import requests
from dotenv import load_dotenv

from crawler.config import CrawlConfig, DomainConfig
from crawler.crawler import CorpusCrawler
from indexing.configs import settings as idx_settings

load_dotenv()

logger = logging.getLogger(__name__)

_SERPAPI_ENDPOINT = "https://serpapi.com/search"


def _serpapi_search_urls(query: str, max_urls: int = 4) -> List[str]:
    """
    Consulta SerpApi (Google) restringida a fuentes médicas confiables y
    devuelve las URLs de los primeros resultados orgánicos.

    Usa 1 búsqueda de la cuota. Devuelve [] si no hay key o si falla.
    """
    api_key = os.getenv(idx_settings.SERPAPI_API_KEY_ENV)
    if not api_key:
        logger.warning("SerpApi: no hay API key configurada (%s).",
                       idx_settings.SERPAPI_API_KEY_ENV)
        return []

    # Restringir a fuentes confiables con OR de site:
    sites = " OR ".join(f"site:{s}" for s in idx_settings.EXPANSION_TRUSTED_SITES)
    full_query = f"{query} ({sites})"

    params = {
        "engine": "google",
        "q": full_query,
        "hl": "es",          # interfaz en español
        "gl": "es",          # geolocalización España (sesga a resultados ES)
        "num": 10,
        "api_key": api_key,
    }

    try:
        resp = requests.get(_SERPAPI_ENDPOINT, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("SerpApi: búsqueda falló: %s", e)
        return []

    organic = data.get("organic_results", []) or []
    urls = []
    for item in organic:
        link = item.get("link")
        if link and link.startswith("http"):
            urls.append(link)
        if len(urls) >= max_urls:
            break

    logger.info("SerpApi: %d URLs obtenidas para '%s'", len(urls), query)
    return urls


def _domains_from_urls(urls: List[str]) -> List[DomainConfig]:
    """
    Construye un DomainConfig por URL. Cada uno se scrapea directamente
    (max_depth=0 en el crawler → no sigue enlaces, solo la URL semilla).
    """
    from urllib.parse import urlparse

    domains = []
    for url in urls:
        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        if not host:
            continue
        domains.append(DomainConfig(
            domain=host,
            seeds=[url],
            language_hint="es",
            source_name=f"{host} (Web)",
            category_hint="health_topic",
            allowed_domains=[host],
        ))
    return domains


def expand_corpus_from_query(
    query: str,
    max_new_docs: int = 2,
    start_doc_id: Optional[int] = None,
) -> List[Dict]:
    """
    Expande el corpus usando SerpApi para encontrar artículos reales en
    fuentes confiables y scrapearlos directamente.

    Args:
        query: Consulta que disparó la expansión.
        max_new_docs: Documentos nuevos objetivo (1-2 basta).
        start_doc_id: id inicial para los docs nuevos (evita colisión con
                      corpus principal y expansión previa).

    Returns:
        Lista de documentos nuevos (vacía si falla).
    """
    logger.info(f"Expansión dinámica (SerpApi) iniciada para: '{query}'")

    # 1) Buscar URLs reales de artículos (1 búsqueda de la cuota)
    urls = _serpapi_search_urls(query, max_urls=4)
    if not urls:
        logger.warning("Expansión: SerpApi no devolvió URLs. Abortando.")
        return []

    # 2) Un DomainConfig por URL, para scrapear directamente
    domains = _domains_from_urls(urls)
    if not domains:
        return []

    # 3) Crawler en modo "scrape directo": depth=0, sin seguir enlaces
    config = CrawlConfig()
    config.max_pages = len(domains) + 2
    config.max_depth = 0           # solo las URLs semilla, no seguir enlaces
    config.delay_seconds = 0.3
    config.min_content_chars = 300
    config.min_valid_documents = max_new_docs
    config.language_targets = {"es": max_new_docs}
    config.relaxed_quality = True  # gate relajado para expansión
    config.output_dir = idx_settings.EXPANSION_DATA_DIR.parent

    try:
        crawler = CorpusCrawler(config=config, domains=domains, scraper=None)
        if start_doc_id is not None:
            crawler.next_doc_id = start_doc_id

        crawler.run()

        new_docs = crawler.valid_docs
        logger.info(f"Expansión completada: {len(new_docs)} documentos nuevos")
        return new_docs

    except Exception as e:
        logger.error(f"Expansión dinámica falló: {e}")
        return []