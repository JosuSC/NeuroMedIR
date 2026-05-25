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
            domain="medlineplus.gov",
            seeds=[
                f"https://medlineplus.gov/?term={url_query}",
                f"https://medlineplus.gov/spanish/?term={url_query}",
            ],
            language_hint="en",
            source_name="MedlinePlus (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["medlineplus.gov"],
        ),
        DomainConfig(
            domain="pubmed.ncbi.nlm.nih.gov",
            seeds=[f"https://pubmed.ncbi.nlm.nih.gov/?term={url_query}"],
            language_hint="en",
            source_name="PubMed (Dinámico)",
            category_hint="research_article",
            allowed_domains=["pubmed.ncbi.nlm.nih.gov"],
        ),
        DomainConfig(
            domain="cdc.gov",
            seeds=[
                f"https://www.cdc.gov/search/?query={url_query}",
                f"https://www.cdc.gov/spanish/search/?query={url_query}",
            ],
            language_hint="en",
            source_name="CDC (Dinámico)",
            category_hint="health_guideline",
            allowed_domains=["cdc.gov"],
        ),
        DomainConfig(
            domain="mayoclinic.org",
            seeds=[f"https://www.mayoclinic.org/search/search-results?q={url_query}"],
            language_hint="en",
            source_name="Mayo Clinic (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["mayoclinic.org"],
        ),
        DomainConfig(
            domain="nhs.uk",
            seeds=[f"https://www.nhs.uk/search/?q={url_query}"],
            language_hint="en",
            source_name="NHS (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["nhs.uk"],
        ),
        DomainConfig(
            domain="msdmanuals.com",
            seeds=[
                f"https://www.msdmanuals.com/searchresults?query={url_query}",
                f"https://www.msdmanuals.com/es/hogar/searchresults?query={url_query}",
            ],
            language_hint="en",
            source_name="MSD Manuals (Dinámico)",
            category_hint="health_topic",
            allowed_domains=["msdmanuals.com"],
        ),
        DomainConfig(
            domain="search.scielo.org",
            seeds=[f"https://search.scielo.org/?q={url_query}"],
            language_hint="es",
            source_name="SciELO (Dinámico)",
            category_hint="research_article",
            allowed_domains=["scielo.org"],
        ),
        DomainConfig(
            domain="paho.org",
            seeds=[f"https://www.paho.org/es/search?keys={url_query}"],
            language_hint="es",
            source_name="OPS/PAHO (Dinámico)",
            category_hint="health_guideline",
            allowed_domains=["paho.org"],
        ),
    ]
    
    # 3. Configuramos un crawler rápido (poca profundidad, documentos limitados)
    config = CrawlConfig()
    config.max_pages = 30         # Revisar más páginas para llegar a contenido útil
    config.max_depth = 2          # Permite seguir resultados hacia páginas finales
    config.delay_seconds = 0.3    # Peticiones rápidas
    config.min_content_chars = 400
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
