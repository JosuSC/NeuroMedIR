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
    max_pages: int = 30000
    request_timeout_seconds: int = 15
    delay_seconds: float = 0.7
    user_agent: str = "NeuroMedIR-CorpusBuilder/2.0"
    max_retries: int = 3
    backoff_base_seconds: float = 1.8
    min_content_chars: int = 600
    min_valid_documents: int = 2500
    language_targets: Dict[str, int] = field(default_factory=lambda: {"es": 2500})
    output_dir: Path = Path("data") / "corpus_v2"
    save_raw_html: bool = False
    relaxed_quality: bool = False  # True en modo expansión: gate menos estricto


DEFAULT_DOMAINS: List[DomainConfig] = [
    DomainConfig(
        domain="medlineplus.gov",
        seeds=[
            "https://medlineplus.gov/spanish/healthtopics.html",
            "https://medlineplus.gov/spanish/encyclopedia.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Aa.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ba.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ca.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Da.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ea.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Fa.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ga.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ha.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ia.html",
            "https://medlineplus.gov/spanish/druginfo/drug_La.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ma.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Na.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Pa.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ra.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Sa.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Ta.html",
            "https://medlineplus.gov/spanish/druginfo/drug_Va.html",
            "https://medlineplus.gov/spanish/ency/encyclopedia_A.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_B.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_C.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_D.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_E.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_G.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_H.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_I.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_M.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_N.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_P.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_R.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_S.htm",
            "https://medlineplus.gov/spanish/ency/encyclopedia_T.htm",
        ]
        + [f"https://medlineplus.gov/spanish/healthtopics_{ch}.html" for ch in "abcdefghijklmnopqrstuvwxyz"],
        language_hint="es",
        source_name="MedlinePlus ES",
        category_hint="health_topic",
        allowed_domains=["medlineplus.gov"],
    ),
    DomainConfig(
        domain="msdmanuals.com",
        seeds=[
            "https://www.msdmanuals.com/es/hogar",
        ],
        language_hint="es",
        source_name="MSD Manuals ES",
        category_hint="health_topic",
        allowed_domains=["msdmanuals.com"],
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
        domain="cdc.gov",
        seeds=[
            "https://www.cdc.gov/spanish/",
            "https://www.cdc.gov/spanish/enfermedades/",
        ],
        language_hint="es",
        source_name="CDC ES",
        category_hint="health_guideline",
        allowed_domains=["cdc.gov"],
    ),
    DomainConfig(
        domain="paho.org",
        seeds=[
            "https://www.paho.org/es/temas",
        ],
        language_hint="es",
        source_name="OPS/PAHO",
        category_hint="health_guideline",
        allowed_domains=["paho.org"],
    ),
   
    DomainConfig(
        domain="cun.es",
        seeds=[
            "https://www.cun.es/enfermedades-tratamientos",
            "https://www.cun.es/enfermedades-tratamientos/enfermedades",
            "https://www.cun.es/enfermedades-tratamientos/tratamientos",
        ],
        language_hint="es",
        source_name="Clínica Universidad de Navarra",
        category_hint="health_topic",
        allowed_domains=["cun.es"],
    ),
    DomainConfig(
        domain="aecc.es",
        seeds=[
            "https://www.aecc.es/es/todo-sobre-cancer",
            "https://www.aecc.es/es/todo-sobre-cancer/tipos-cancer",
            "https://www.aecc.es/es/todo-sobre-cancer/vivir-con-cancer",
        ],
        language_hint="es",
        source_name="AECC",
        category_hint="health_topic",
        allowed_domains=["aecc.es"],
    ),
    DomainConfig(
        domain="fundaciondelcorazon.com",
        seeds=[
            "https://fundaciondelcorazon.com/informacion-para-pacientes.html",
            "https://fundaciondelcorazon.com/enfermedades-cardiovasculares.html",
            "https://fundaciondelcorazon.com/prevencion.html",
        ],
        language_hint="es",
        source_name="Fundación Española del Corazón",
        category_hint="health_topic",
        allowed_domains=["fundaciondelcorazon.com"],
    ),
    DomainConfig(
        domain="intramed.net",
        seeds=[
            "https://www.intramed.net/",
            "https://www.intramed.net/sitios/listaarticulos.asp?carpetaID=3",
            "https://www.intramed.net/sitios/listaarticulos.asp?carpetaID=6",
        ],
        language_hint="es",
        source_name="IntraMed",
        category_hint="research_article",
        allowed_domains=["intramed.net"],
    ),
    DomainConfig(
        domain="medicosypacientes.com",
        seeds=[
            "https://www.medicosypacientes.com/",
            "https://www.medicosypacientes.com/categoria/enfermedades",
        ],
        language_hint="es",
        source_name="Médicos y Pacientes",
        category_hint="health_topic",
        allowed_domains=["medicosypacientes.com"],
    ),
    DomainConfig(
        domain="salud.mapfre.es",
        seeds=[
            "https://www.salud.mapfre.es/enfermedades/",
            "https://www.salud.mapfre.es/medicamentos/",
            "https://www.salud.mapfre.es/sintomas/",
        ],
        language_hint="es",
        source_name="MAPFRE Salud",
        category_hint="health_topic",
        allowed_domains=["salud.mapfre.es"],
    ),
    DomainConfig(
        domain="tuotromedico.com",
        seeds=[
            "https://www.tuotromedico.com/temas/",
            "https://www.tuotromedico.com/enfermedades/",
        ],
        language_hint="es",
        source_name="Tu Otro Médico",
        category_hint="health_topic",
        allowed_domains=["tuotromedico.com"],
    ),
    DomainConfig(
        domain="semergen.es",
        seeds=[
            "https://www.semergen.es/index.php/es/pacientes",
        ],
        language_hint="es",
        source_name="SEMERGEN",
        category_hint="health_guideline",
        allowed_domains=["semergen.es"],
    ),
    # DomainConfig(
    #     domain="medlineplus.gov",
    #     seeds=[
    #         "https://medlineplus.gov/healthtopics.html",
    #         "https://medlineplus.gov/encyclopedia.html",
    #     ],
    #     language_hint="en",
    #     source_name="MedlinePlus",
    #     category_hint="health_topic",
    #     allowed_domains=["medlineplus.gov"],
    # ),
    # DomainConfig(
    #     domain="pubmed.ncbi.nlm.nih.gov",
    #     seeds=[
    #         "https://pubmed.ncbi.nlm.nih.gov/trending/",
    #         "https://pubmed.ncbi.nlm.nih.gov/?term=medicine",
    #         "https://pubmed.ncbi.nlm.nih.gov/?term=public+health",
    #     ],
    #     language_hint="en",
    #     source_name="PubMed",
    #     category_hint="research_article",
    #     allowed_domains=["pubmed.ncbi.nlm.nih.gov"],
    # ),
    # DomainConfig(
    #     domain="nih.gov",
    #     seeds=[
    #         "https://www.nih.gov/health-information",
    #         "https://newsinhealth.nih.gov/",
    #     ],
    #     language_hint="en",
    #     source_name="NIH",
    #     category_hint="health_guideline",
    #     allowed_domains=["nih.gov", "newsinhealth.nih.gov"],
    # ),
    # DomainConfig(
    #     domain="msdmanuals.com",
    #     seeds=[
    #         "https://www.msdmanuals.com/professional",
    #         "https://www.msdmanuals.com/home",
    #     ],
    #     language_hint="en",
    #     source_name="MSD Manuals",
    #     category_hint="health_topic",
    #     allowed_domains=["msdmanuals.com"],
    # ),
    # DomainConfig(
    #     domain="cdc.gov",
    #     seeds=[
    #         "https://www.cdc.gov/",
    #         "https://www.cdc.gov/healthinformation/",
    #     ],
    #     language_hint="en",
    #     source_name="CDC",
    #     category_hint="health_guideline",
    #     allowed_domains=["cdc.gov"],
    # ),
    # DomainConfig(
    #     domain="mayoclinic.org",
    #     seeds=[
    #         "https://www.mayoclinic.org/diseases-conditions",
    #         "https://www.mayoclinic.org/symptom-checker",
    #     ],
    #     language_hint="en",
    #     source_name="Mayo Clinic",
    #     category_hint="health_topic",
    #     allowed_domains=["mayoclinic.org"],
    # ),
    # DomainConfig(
    #     domain="nhs.uk",
    #     seeds=[
    #         "https://www.nhs.uk/conditions/",
    #     ],
    #     language_hint="en",
    #     source_name="NHS",
    #     category_hint="health_topic",
    #     allowed_domains=["nhs.uk"],
    # ),
]


def default_crawl_config() -> CrawlConfig:
    cfg = CrawlConfig()
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    return cfg