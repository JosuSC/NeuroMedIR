"""
selectors.py — Selectores CSS por dominio para extracción de contenido.

Cada dominio médico estructura su contenido de forma distinta.
Este módulo centraliza la configuración de selectores para que el scraper
sepa exactamente dónde buscar el contenido principal en cada sitio.

Para añadir un nuevo dominio:
    1. Añadir el dominio como clave en DOMAIN_SELECTORS
    2. Listar los selectores CSS en orden de prioridad (más específico primero)
    3. El scraper intenta cada selector en orden y se queda con el primero
       que produzca contenido mayor a 120 caracteres

Selectores comunes:
    - "main"             → etiqueta <main> (HTML5 semántico)
    - "article"          → etiqueta <article> (HTML5 semántico)
    - "#topic-summary"   → elemento con id="topic-summary"
    - ".abstract"        → elementos con class="abstract"
    - "body"             → fallback final (todo el body)
"""

# Selectores CSS por dominio, ordenados por prioridad (más específico primero).
# El scraper recorre la lista y usa el primer selector que produzca
# contenido con más de 120 caracteres.
DOMAIN_SELECTORS = {
    "pubmed.ncbi.nlm.nih.gov": [
        "main",
        "article",
        "section.abstract",
        "div.abstract-content",
    ],
    "medlineplus.gov": [
        "div#topic-summary",
        "div.topic-summary",
        "div#health-topic-content",
        "section#about",
        "div.main-content",
        "article",
        "main",
        "body",
    ],
    "who.int": [
        "main",
        "article",
        "div.sf_colsIn",
        "body",
    ],
    "nih.gov": [
        "main",
        "article",
        "div.article-content",
        "body",
    ],
    "cdc.gov": [
        "main",
        "article",
        "#main-content",
        "body",
    ],
    "mayoclinic.org": [
        "main",
        "article",
        "div.content",
        "body",
    ],
    "nhs.uk": [
        "main",
        "article",
        "#main-content",
        "body",
    ],
    "msdmanuals.com": [
        "main",
        "article",
        "div#main-content",
        "div.article-content",
        "body",
    ],
    "scielo.org": [
        "main",
        "article",
        "#articleText",
        "body",
    ],
    "paho.org": [
        "main",
        "article",
        "div.main-content",
        "body",
    ],
    "cun.es": [
        "div.content-detail",
        "div.field-items",
        "article",
        "main",
        "body",
    ],
    "aecc.es": [
        "div.content-body",
        "div.field-body",
        "article",
        "main",
        "body",
    ],
    "fundaciondelcorazon.com": [
        "div.entry-content",
        "div.article-body",
        "article",
        "main",
        "body",
    ],
    "intramed.net": [
        "div#divArticulo",
        "div.articulo-contenido",
        "div.content",
        "article",
        "main",
        "body",
    ],
    "medicosypacientes.com": [
        "div.entry-content",
        "div.post-content",
        "article",
        "main",
        "body",
    ],
    "salud.mapfre.es": [
        "div.article__body",
        "div.content-body",
        "article",
        "main",
        "body",
    ],
    "tuotromedico.com": [
        "div.entry-content",
        "div.post-body",
        "article",
        "main",
        "body",
    ],
    "semergen.es": [
        "div.content",
        "div.article-body",
        "article",
        "main",
        "body",
    ],
    "scielo.br": [
        "div#articleText",
        "article",
        "main",
        "body",
    ],
    "scielo.cl": [
        "div#articleText",
        "article",
        "main",
        "body",
    ],
    "scielo.isciii.es": [
        "div#articleText",
        "article",
        "main",
        "body",
    ],
    "scielo.sld.cu": [
        "div#articleText",
        "article",
        "main",
        "body",
    ],
}

