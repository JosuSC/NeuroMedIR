import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .utils import strip_noise


"""
scraper.py — Scraper ligero por dominio.

La idea aquí es tener una capa simple que haga tres cosas:
1) descargar una página,
2) extraer enlaces útiles,
3) sacar título y contenido principal sin contaminarlo con ruido.

No intento hacer una extracción perfecta; prefiero algo robusto y fácil de
mantener para este proyecto.
"""

DOMAIN_SELECTORS = {
    "pubmed.ncbi.nlm.nih.gov": ["main", "article", "section.abstract", "div.abstract-content"],
    "medlineplus.gov": ["main", "article", "#topic-summary", "body"],
    "who.int": ["main", "article", "div.sf_colsIn", "body"],
    "nih.gov": ["main", "article", "div.article-content", "body"],
    "scielo.org": ["main", "article", "#articleText", "body"],
}


class DomainScraper:
    """Scraper con reintentos, extracción de links y parseo de contenido.

    Lo separo del crawler para que el crawler solo coordine el flujo y este
    objeto se encargue de la parte HTTP/HTML.
    """

    def __init__(self, timeout: int = 15, max_retries: int = 3, backoff_base_seconds: float = 1.8):
        """Configura tiempos de espera y política de reintentos."""
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds

    def fetch(self, url: str, headers: Dict[str, str]) -> Optional[requests.Response]:
        """Hace la petición HTTP con tolerancia básica a fallos transitorios."""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(self.backoff_base_seconds ** attempt)
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status is None or status < 500 or attempt == self.max_retries - 1:
                    return None
                time.sleep(self.backoff_base_seconds ** attempt)
            except requests.RequestException:
                return None
        return None

    def extract_links(self, html: str, base_url: str) -> List[str]:
        """Extrae enlaces absolutos del HTML y evita duplicados."""
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href:
                continue
            full = urljoin(base_url, href).split("#")[0]
            if full.startswith("http"):
                links.add(full)
        return list(links)

    def parse_content(self, html: str, source_domain: str) -> Dict[str, str]:
        """Saca título y cuerpo principal desde una página HTML.

        Uso selectores por dominio porque cada sitio médico estructura el
        contenido de forma distinta y eso mejora bastante la extracción.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Quito ruido visual y scripts para quedarme con el contenido útil
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = strip_noise(title_tag.get_text(" "))

        selectors = DOMAIN_SELECTORS.get(source_domain, ["main", "article", "body"])
        content_text = ""

        for selector in selectors:
            selected = soup.select_one(selector)
            if selected:
                content_text = strip_noise(selected.get_text(" "))
                if len(content_text) > 120:
                    break

        return {
            "title": title,
            "content": content_text,
        }
