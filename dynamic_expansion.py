import logging
from typing import List, Dict
from urllib.parse import quote_plus
from crawler.config import CrawlConfig, DomainConfig
from crawler.crawler import CorpusCrawler

logger = logging.getLogger(__name__)

def expand_corpus_from_query(query: str, max_new_docs: int = 5) -> List[Dict]:
    """
    Expande el corpus dinámicamente usando la consulta del usuario.
    Toma la consulta, genera URLs de búsqueda y arranca el crawler en tiempo real.
    """
    logger.info(f"Iniciando expansión dinámica para la consulta: '{query}'")
    
    # 1. Convertimos la consulta en un formato válido para URLs
    url_query = quote_plus(query.lower())
    
    # 2. Generamos dominios semilla web específicos para esta consulta
    dynamic_domains = [
        DomainConfig(
            domain="pubmed.ncbi.nlm.nih.gov",
            seeds=[f"https://pubmed.ncbi.nlm.nih.gov/?term={url_query}"],
            language_hint="en",
            source_name="PubMed (Dinámico)",
            category_hint="research_article",
            allowed_domains=["pubmed.ncbi.nlm.nih.gov"],
        ),
        DomainConfig(
            domain="search.scielo.org",
            seeds=[f"https://search.scielo.org/?q={url_query}"],
            language_hint="es",
            source_name="SciELO (Dinámico)",
            category_hint="research_article",
            allowed_domains=["scielo.org"],
        )
    ]
    
    # 3. Configuramos un crawler rápido (solo profundidad 1, y pocos documentos)
    config = CrawlConfig()
    config.max_pages = 10         # Solo revisa un máximo de 10 páginas para ser rápido
    config.max_depth = 1          # No entrar muy profundo
    config.delay_seconds = 0.2    # Peticiones rápidas
    config.min_valid_documents = max_new_docs
    config.language_targets = {}  # Ignorar lÃmites de balance para que no rechace por haber llegado a 2000
    
    # 4. Instanciamos y ejecutamos el crawler con esta configuración
    try:
        crawler = CorpusCrawler(config=config, domains=dynamic_domains)
        crawler.run()
        logger.info(f"Expansión terminada. Se añadieron {len(crawler.valid_docs)} nuevos documentos al corpus.")
        return crawler.valid_docs
    except Exception as e:
        logger.error(f"Error durante la expansión dinámica: {e}")
        return []
