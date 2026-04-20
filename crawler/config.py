from dataclasses import dataclass, field
from pathlib import Path
import string
from typing import Dict, List


@dataclass(frozen=True)
class DomainConfig:
    domain: str
    seeds: List[str]
    language_hint: str
    source_name: str
    category_hint: str
    allowed_domains: List[str] = field(default_factory=list)


@dataclass
class CrawlConfig:
    max_depth: int = 3
    max_pages: int = 20000
    request_timeout_seconds: int = 15
    delay_seconds: float = 1.0
    user_agent: str = "NeuroMedIR-CorpusBuilder/2.0"
    max_retries: int = 3
    backoff_base_seconds: float = 1.8
    min_content_chars: int = 600
    min_valid_documents: int = 2000
    language_targets: Dict[str, int] = field(default_factory=lambda: {"en": 1200, "es": 800})
    output_dir: Path = Path("data") / "corpus_v2"
    save_raw_html: bool = False


DEFAULT_DOMAINS: List[DomainConfig] = [
    DomainConfig(
        domain="medlineplus.gov",
        seeds=[
            "https://medlineplus.gov/healthtopics.html",
            "https://medlineplus.gov/encyclopedia.html",
        ],
        language_hint="en",
        source_name="MedlinePlus",
        category_hint="health_topic",
        allowed_domains=["medlineplus.gov"],
    ),
    DomainConfig(
        domain="pubmed.ncbi.nlm.nih.gov",
        seeds=[
            "https://pubmed.ncbi.nlm.nih.gov/trending/",
            "https://pubmed.ncbi.nlm.nih.gov/?term=medicine",
            "https://pubmed.ncbi.nlm.nih.gov/?term=public+health",
        ],
        language_hint="en",
        source_name="PubMed",
        category_hint="research_article",
        allowed_domains=["pubmed.ncbi.nlm.nih.gov"],
    ),
    DomainConfig(
        domain="nih.gov",
        seeds=[
            "https://www.nih.gov/health-information",
            "https://newsinhealth.nih.gov/",
        ],
        language_hint="en",
        source_name="NIH",
        category_hint="health_guideline",
        allowed_domains=["nih.gov", "newsinhealth.nih.gov"],
    ),
    DomainConfig(
        domain="medlineplus.gov",
        seeds=["https://medlineplus.gov/spanish/healthtopics.html", "https://medlineplus.gov/spanish/encyclopedia.html"]
        + [f"https://medlineplus.gov/spanish/healthtopics_{ch}.html" for ch in string.ascii_lowercase],
        language_hint="es",
        source_name="MedlinePlus ES",
        category_hint="health_topic",
        allowed_domains=["medlineplus.gov"],
    ),
    DomainConfig(
        domain="who.int",
        seeds=[
            "https://www.who.int/es/health-topics",
            "https://www.who.int/es/news-room",
        ],
        language_hint="es",
        source_name="OMS",
        category_hint="health_guideline",
        allowed_domains=["who.int"],
    ),
    DomainConfig(
        domain="scielo.org",
        seeds=[
            "https://scielo.org/es/",
            "https://search.scielo.org/?q=salud&lang=es",
            "https://search.scielo.org/?q=medicina&lang=es",
            "https://search.scielo.org/?q=epidemiologia&lang=es",
            "https://search.scielo.org/?q=atencion+primaria&lang=es",
        ],
        language_hint="es",
        source_name="SciELO",
        category_hint="research_article",
        allowed_domains=[
            "scielo.org",
            "scielo.br",
            "scielo.cl",
            "scielo.isciii.es",
            "scielo.sld.cu",
            "scielo.sa.cr",
            "scielo.org.mx",
        ],
    ),
]


def default_crawl_config() -> CrawlConfig:
    cfg = CrawlConfig()
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    return cfg
