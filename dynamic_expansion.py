"""
dynamic_expansion.py — Expansión dinámica del corpus para NeuroMedIR.

Se activa automáticamente cuando el corpus local es insuficiente para
responder una consulta. Hace un crawling ligero y rápido sobre fuentes
médicas confiables, priorizando español, e indexa los resultados para
uso futuro.
"""

import logging
from typing import List, Dict
from urllib.parse import quote_plus

from crawler.config import CrawlConfig, DomainConfig
from crawler.crawler import CorpusCrawler
from indexing.configs import settings as idx_settings

logger = logging.getLogger(__name__)

# Fuentes estáticas en español para expansión — se usan siempre
_SPANISH_STATIC_DOMAINS = [
    DomainConfig(
        domain="cun.es",
        seeds=["https://www.cun.es/enfermedades-tratamientos"],
        language_hint="es",
        source_name="Clínica Universidad de Navarra",
        category_hint="health_topic",
        allowed_domains=["cun.es"],
    ),
    DomainConfig(
        domain="aecc.es",
        seeds=["https://www.aecc.es/es/todo-sobre-cancer"],
        language_hint="es",
        source_name="AECC",
        category_hint="health_topic",
        allowed_domains=["aecc.es"],
    ),
    DomainConfig(
        domain="fundaciondelcorazon.com",
        seeds=["https://fundaciondelcorazon.com/informacion-para-pacientes.html"],
        language_hint="es",
        source_name="Fundación Española del Corazón",
        category_hint="health_topic",
        allowed_domains=["fundaciondelcorazon.com"],
    ),
    DomainConfig(
        domain="semergen.es",
        seeds=["https://www.semergen.es/index.php/es/pacientes"],
        language_hint="es",
        source_name="SEMERGEN",
        category_hint="health_guideline",
        allowed_domains=["semergen.es"],
    ),
    DomainConfig(
        domain="intramed.net",
        seeds=["https://www.intramed.net/"],
        language_hint="es",
        source_name="IntraMed",
        category_hint="research_article",
        allowed_domains=["intramed.net"],
    ),
]


def _build_dynamic_domains(url_query: str) -> List[DomainConfig]:
    """
    Construye dominios de búsqueda dinámica para la consulta dada.
    Combina fuentes en español e inglés con la query del usuario.
    """
    return [
        # --- Español (prioritario) ---
        DomainConfig(
            domain="medlineplus.gov",
            seeds=[
                f"https://medlineplus.gov/spanish/search/?query={url_query}",
                f"https://medlineplus.gov/spanish/?term={url_query}",
            ],
            language_hint="es",
            source_name="MedlinePlus ES (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["medlineplus.gov"],
        ),
        DomainConfig(
            domain="cdc.gov",
            seeds=[
                f"https://www.cdc.gov/spanish/search/?query={url_query}",
            ],
            language_hint="es",
            source_name="CDC ES (Dinámico)",
            category_hint="health_guideline",
            allowed_domains=["cdc.gov"],
        ),
        DomainConfig(
            domain="paho.org",
            seeds=[
                f"https://www.paho.org/es/search?keys={url_query}",
            ],
            language_hint="es",
            source_name="OPS/PAHO (Dinámico)",
            category_hint="health_guideline",
            allowed_domains=["paho.org"],
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
        DomainConfig(
            domain="who.int",
            seeds=[
                f"https://www.who.int/es/search?query={url_query}",
            ],
            language_hint="es",
            source_name="OMS (Dinámico)",
            category_hint="health_guideline",
            allowed_domains=["who.int"],
        ),
      
        # --- Inglés (complementario) ---
        DomainConfig(
            domain="medlineplus.gov",
            seeds=[
                f"https://medlineplus.gov/?term={url_query}",
            ],
            language_hint="en",
            source_name="MedlinePlus (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["medlineplus.gov"],
        ),
        DomainConfig(
            domain="pubmed.ncbi.nlm.nih.gov",
            seeds=[
                f"https://pubmed.ncbi.nlm.nih.gov/?term={url_query}",
            ],
            language_hint="en",
            source_name="PubMed (Dinámico)",
            category_hint="research_article",
            allowed_domains=["pubmed.ncbi.nlm.nih.gov"],
        ),
        DomainConfig(
            domain="mayoclinic.org",
            seeds=[
                f"https://www.mayoclinic.org/search/search-results?q={url_query}",
            ],
            language_hint="en",
            source_name="Mayo Clinic (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["mayoclinic.org"],
        ),
    ]


def expand_corpus_from_query(query: str, max_new_docs: int = 5) -> List[Dict]:
    """
    Expande el corpus dinámicamente usando la consulta del usuario.

    Flujo:
        1. Construir dominios de búsqueda específicos para la query
        2. Añadir fuentes estáticas en español de alta calidad
        3. Ejecutar crawling ligero (profundidad baja, sin cargar corpus previo)
        4. Retornar documentos nuevos para que api.py los indexe

    Args:
        query: Consulta del usuario que disparó la expansión.
        max_new_docs: Número mínimo de documentos nuevos a obtener.

    Returns:
        Lista de documentos nuevos (puede estar vacía si falla el crawling).
    """
    logger.info(f"Expansión dinámica iniciada para: '{query}'")

    url_query = quote_plus(query.lower().strip())

    # Combinar dominios dinámicos (query-specific) con estáticos (español fijo)
    dynamic_domains = _build_dynamic_domains(url_query)
    all_domains = dynamic_domains + _SPANISH_STATIC_DOMAINS

    # Configuración ligera para expansión en tiempo real
    config = CrawlConfig()
    config.max_pages = 25
    config.max_depth = 1          # Solo páginas de resultados, no seguir enlaces
    config.delay_seconds = 0.3
    config.min_content_chars = 400
    config.min_valid_documents = max_new_docs
    # Sin límites de idioma para no rechazar documentos válidos en expansión
    config.language_targets = {"es": max_new_docs, "en": max(1, max_new_docs - 2)}
    # Directorio separado para no mezclar con el corpus base durante la expansión
    config.output_dir = idx_settings.EXPANSION_DATA_DIR

    try:
        # IMPORTANTE: skip_existing=True evita cargar todo el corpus en memoria
        # El crawler solo trabaja con los documentos nuevos de esta sesión
        crawler = CorpusCrawler(
            config=config,
            domains=all_domains,
            scraper=None,  # Usa el scraper por defecto
        )
        # Limpiar estado previo para que esta expansión sea independiente
        # (no necesitamos el historial del corpus completo aquí)
        crawler.valid_docs = []
        crawler.visited = set()

        crawler.run()

        new_docs = crawler.valid_docs
        logger.info(
            f"Expansión completada: {len(new_docs)} documentos nuevos "
            f"(es={sum(1 for d in new_docs if d.get('language') == 'es')}, "
            f"en={sum(1 for d in new_docs if d.get('language') == 'en')})"
        )
        return new_docs

    except Exception as e:
        logger.error(f"Expansión dinámica falló: {e}")
        return []