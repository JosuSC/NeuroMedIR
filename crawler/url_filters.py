"""
url_filters.py — Reglas de exclusión de URLs de bajo valor semántico.

Estas URLs suelen corresponder a:
- índices alfabéticos
- hubs de navegación
- directorios
- páginas browse
- taxonomías del sitio
- páginas legales
- páginas de navegación médica masiva

Objetivo:
Excluir páginas que contaminan embeddings y degradan retrieval
en sistemas RAG biomédicos.

IMPORTANTE:
Este filtrado ocurre ANTES del fetch, por lo que:
- ahorra ancho de banda
- reduce parseo inútil
- mejora calidad global del corpus
"""

import re
from typing import List, Pattern


# ============================================================
# PATRONES DE EXCLUSIÓN
# ============================================================

URL_EXCLUDE_PATTERNS: List[Pattern] = [

    # ========================================================
    # MEDLINEPLUS — ÍNDICES ALFABÉTICOS
    # ========================================================

    # healthtopics_a.html
    # healthtopics_b.html
    re.compile(
        r"healthtopics_[a-z]\.html$",
        re.IGNORECASE,
    ),

    # ========================================================
    # MEDLINEPLUS — DIRECTORIOS DE MEDICAMENTOS
    # ========================================================

    # drug_A.html
    # drug_Ba.html
    # drug_Xy.html
    re.compile(
        r"drug_[a-z]{1,2}\.html$",
        re.IGNORECASE,
    ),

    # ========================================================
    # ENCICLOPEDIAS / ÍNDICES GLOBALES
    # ========================================================

    re.compile(
        r"/encyclopedia(\.html)?$",
        re.IGNORECASE,
    ),

    re.compile(
        r"/medical-encyclopedia",
        re.IGNORECASE,
    ),

    # ========================================================
    # BROWSE / ALL TOPICS / DIRECTORIOS
    # ========================================================

    re.compile(
        r"/browse",
        re.IGNORECASE,
    ),

    re.compile(
        r"/all-topics",
        re.IGNORECASE,
    ),

    re.compile(
        r"/topics/?$",
        re.IGNORECASE,
    ),

    re.compile(
        r"/healthtopics(\.html)?$",
        re.IGNORECASE,
    ),

    # ========================================================
    # PÁGINAS DE NAVEGACIÓN MASIVA
    # ========================================================

    # Ejemplo:
    # earnoseandthroat.html
    # bonesjointsandmuscles.html
    re.compile(
        r"/[a-z]+and[a-z]+(\.html)?$",
        re.IGNORECASE,
    ),

    # ========================================================
    # LISTADOS / DIRECTORIOS
    # ========================================================

    re.compile(
        r"/directory",
        re.IGNORECASE,
    ),

    

    re.compile(
        r"/sitemap",
        re.IGNORECASE,
    ),

    re.compile(
        r"/archives?",
        re.IGNORECASE,
    ),

    # ========================================================
    # TAGS / CATEGORÍAS / TAXONOMÍAS
    # ========================================================

    re.compile(
        r"/tags?/",
        re.IGNORECASE,
    ),

    re.compile(
        r"/categories?/",
        re.IGNORECASE,
    ),

    

    # ========================================================
    # PÁGINAS LEGALES / BOILERPLATE
    # ========================================================

    re.compile(
        r"/privacy",
        re.IGNORECASE,
    ),

    re.compile(
        r"/terms",
        re.IGNORECASE,
    ),

    re.compile(
        r"/legal",
        re.IGNORECASE,
    ),

    re.compile(
        r"/copyright",
        re.IGNORECASE,
    ),

    re.compile(
        r"/disclaimer",
        re.IGNORECASE,
    ),

    re.compile(
        r"/accessibility",
        re.IGNORECASE,
    ),

    # ========================================================
    # LOGIN / ACCOUNT / SYSTEM
    # ========================================================

    re.compile(
        r"/login",
        re.IGNORECASE,
    ),

    re.compile(
        r"/signin",
        re.IGNORECASE,
    ),

    re.compile(
        r"/signup",
        re.IGNORECASE,
    ),

    re.compile(
        r"/account",
        re.IGNORECASE,
    ),

   

    # ========================================================
    # PAGINACIÓN
    # ========================================================

    re.compile(
        r"[?&]page=\d+",
        re.IGNORECASE,
    ),

    # ========================================================
    # PRINT / SHARE / AMP
    # ========================================================

    re.compile(
        r"/print",
        re.IGNORECASE,
    ),

    re.compile(
        r"/amp/?$",
        re.IGNORECASE,
    ),
    
    # Páginas de búsqueda con resultados paginados (no semillas de búsqueda)
    re.compile(
        r"/search/?\?.*page=\d+",
        re.IGNORECASE,
    ),

    # Índices de enciclopedia alfabéticos (encyclopedia_A.htm, encyclopedia_B.htm)
    re.compile(
        r"/ency/encyclopedia_[a-z]\.htm$",
        re.IGNORECASE,
    ),
    
    # Páginas "about", "acerca de", recursos institucionales
    re.compile(
        r"/about",
        re.IGNORECASE,
    ),
    re.compile(
        r"/resourcespages",
        re.IGNORECASE,
    ),
    re.compile(
        r"/vida-saludable$",
        re.IGNORECASE,
    ),
    
]


# ============================================================
# API PRINCIPAL
# ============================================================

def should_skip_url(url: str) -> bool:
    """
    Determina si una URL debe excluirse del crawling.

    El filtrado es puramente heurístico basado en patrones
    de bajo valor semántico observados en corpus médicos web.

    Args:
        url:
            URL absoluta.

    Returns:
        True si debe excluirse del crawling.
    """
    return any(
        pattern.search(url)
        for pattern in URL_EXCLUDE_PATTERNS
    )