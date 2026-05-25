"""
scraper.py — Scraper de contenido web por dominio para NeuroMedIR.

Responsabilidades exclusivas de scraping (NO crawling):
    1. Descargar una página web con reintentos y backoff exponencial
    2. Extraer enlaces absolutos desde HTML
    3. Extraer título y contenido principal usando selectores CSS por dominio

Este módulo NO sabe nada de colas BFS, robots.txt, ni balance de idiomas.
Eso es responsabilidad del crawler. Aquí solo se hace fetch/parse/extract.

Complejidad algorítmica:
    - fetch():          O(max_reintentos) con backoff exponencial
    - extract_links():  O(n) donde n = número de etiquetas <a> en el HTML
    - parse_content():  O(longitud_html) con BeautifulSoup
"""

import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .utils import strip_noise, setup_logger
from .configs.selectors import DOMAIN_SELECTORS

logger = setup_logger(__name__)


class DomainScraper:
    """Scraper con reintentos, extracción de enlaces y parseo de contenido.

    Separa la lógica HTTP/HTML del crawler para que el crawler solo
    coordine el flujo BFS y este objeto maneje la comunicación web.

    Se puede usar de forma independiente:

        scraper = DomainScraper()
        respuesta = scraper.fetch("https://medlineplus.gov/...", headers={...})
        enlaces = scraper.extract_links(respuesta.text, base_url="...")
        contenido = scraper.parse_content(respuesta.text, source_domain="medlineplus.gov")

    O inyectado en el crawler:

        crawler = CorpusCrawler(config=config, scraper=DomainScraper())
    """

    def __init__(
        self,
        timeout: int = 15,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.8,
    ):
        """Configura tiempos de espera y política de reintentos.

        Args:
            timeout: Segundos máximos de espera por cada petición HTTP.
            max_retries: Número máximo de reintentos ante errores transitorios.
            backoff_base_seconds: Base para el backoff exponencial.
                                  El delay entre reintentos es base^intento.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds

    def fetch(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[requests.Response]:
        """Realiza la petición HTTP con tolerancia a fallos transitorios.

        Política de reintentos:
            - Timeouts: reintenta con backoff exponencial.
            - Errores 5xx (server): reintenta con backoff exponencial.
            - Errores 4xx (client): falla inmediatamente, no son transitorios.
            - Otros errores de red: falla inmediatamente.

        Complejidad: O(max_retries) en el peor caso.

        Args:
            url: URL absoluta a descargar.
            headers: Headers HTTP (debe incluir User-Agent).

        Returns:
            Objeto Response si fue exitoso, None si falla definitivamente.
        """
        for intento in range(self.max_retries):
            try:
                respuesta = requests.get(
                    url, headers=headers, timeout=self.timeout
                )
                respuesta.raise_for_status()

                # Forzar decodificación coherente para evitar mojibake en páginas ES.
                if not respuesta.encoding or respuesta.encoding.lower() == "iso-8859-1":
                    apparent = getattr(respuesta, "apparent_encoding", None)
                    if apparent:
                        respuesta.encoding = apparent

                return respuesta

            except requests.exceptions.Timeout:
                if intento == self.max_retries - 1:
                    logger.warning(
                        "Timeout definitivo tras %d intentos: %s",
                        self.max_retries, url,
                    )
                    return None
                delay = self.backoff_base_seconds ** intento
                logger.debug(
                    "Timeout en %s (intento %d/%d). Reintentando en %.1fs...",
                    url, intento + 1, self.max_retries, delay,
                )
                time.sleep(delay)

            except requests.exceptions.HTTPError as exc:
                estado = (
                    exc.response.status_code
                    if exc.response is not None
                    else None
                )
                # Errores 4xx son del cliente, no tienen sentido reintentar
                if estado is None or estado < 500 or intento == self.max_retries - 1:
                    logger.debug("HTTP %s en %s: fallo sin reintento.", estado, url)
                    return None
                delay = self.backoff_base_seconds ** intento
                logger.debug(
                    "HTTP %d en %s (intento %d/%d). Reintentando en %.1fs...",
                    estado, url, intento + 1, self.max_retries, delay,
                )
                time.sleep(delay)

            except requests.RequestException as exc:
                logger.debug("Error de red en %s: %s", url, exc)
                return None

        return None

    def extract_links(self, html: str, base_url: str) -> List[str]:
        """Extrae enlaces absolutos y únicos desde el HTML.

        Resuelve URLs relativas contra la base_url, elimina fragmentos (#)
        para evitar duplicar la misma página, y filtra solo esquemas HTTP.

        Complejidad: O(n) donde n = número de etiquetas <a> con href.

        Args:
            html: Contenido HTML completo de la página.
            base_url: URL base para resolver enlaces relativos.

        Returns:
            Lista de URLs absolutas únicas (sin fragmentos).
        """
        soup = BeautifulSoup(html, "html.parser")
        enlaces = set()

        for etiqueta_a in soup.find_all("a", href=True):
            href = etiqueta_a["href"].strip()
            if not href:
                continue
            # Resolver URL relativa → absoluta y eliminar fragmento
            url_completa = urljoin(base_url, href).split("#")[0]
            if url_completa.startswith("http"):
                enlaces.add(url_completa)

        return list(enlaces)

    def parse_content(
        self, html: str, source_domain: str = ""
    ) -> Dict[str, str]:
        """Extrae título y cuerpo principal desde una página HTML.

        Utiliza selectores CSS específicos por dominio para localizar
        el contenido principal. Cada sitio médico estructura sus páginas
        de forma distinta, por eso los selectores son por dominio.

        Algoritmo:
            1. Eliminar etiquetas de ruido (script, style, nav, etc.)
            2. Extraer el título de la etiqueta <title>
            3. Probar cada selector CSS en orden de prioridad
            4. Quedarse con el primer selector que produzca >120 caracteres
            5. Si ningún selector funciona, fallback a "body"

        Complejidad: O(longitud_html) por el parsing de BeautifulSoup.

        Args:
            html: Contenido HTML completo de la página.
            source_domain: Dominio fuente (ej. "pubmed.ncbi.nlm.nih.gov")
                           para seleccionar los CSS selectors apropiados.

        Returns:
            Diccionario con {"title": str, "content": str}.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Eliminar etiquetas que no aportan contenido textual
        for etiqueta in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            etiqueta.decompose()

        # Extraer título
        titulo = ""
        etiqueta_titulo = soup.find("title")
        if etiqueta_titulo:
            titulo = strip_noise(etiqueta_titulo.get_text(" "))

        # Seleccionar los selectores CSS según el dominio
        selectores = DOMAIN_SELECTORS.get(source_domain, ["main", "article", "body"])
        contenido_texto = ""

        for selector in selectores:
            elemento = soup.select_one(selector)
            if elemento:
                contenido_texto = strip_noise(elemento.get_text(" "))
                # Umbral de 120 chars: evita aceptar selectores que
                # coinciden con elementos vacíos o casi vacíos
                if len(contenido_texto) > 120:
                    break

        return {
            "title": titulo,
            "content": contenido_texto,
        }

