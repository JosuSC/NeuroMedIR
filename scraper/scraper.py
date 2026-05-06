import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .utils import clean_text, setup_logger
from .document_classifier import DocumentClassifier

logger = setup_logger(__name__)

class Scraper:
    def __init__(self, max_retries: int = 3, backoff_base: float = 2.0):
        """
        Args:
            max_retries: Número máximo de reintentos para errores transitorios.
            backoff_base: Base para el backoff exponencial (delay = backoff_base ** attempt).
        """
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.classifier = DocumentClassifier()

    def fetch_page(self, url: str, headers: dict, timeout: int = 10) -> requests.Response:
        """
        Hace un GET request a la URL dada con reintentos y backoff exponencial.
        
        Reintentos se aplican para errores transitorios (5xx, timeout).
        Errores 4xx o de red permanentes fallan inmediatamente.
        
        Retorna el objeto Response si fue exitoso, None si falla.
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()  # Lanza excepción para códigos 4xx/5xx
                return response
            except requests.exceptions.Timeout as e:
                # Reintento en timeout
                if attempt < self.max_retries - 1:
                    delay = self.backoff_base ** attempt
                    logger.warning(
                        f"Timeout al obtener {url} (intento {attempt + 1}/{self.max_retries}). "
                        f"Reintentando en {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Timeout definitivo tras {self.max_retries} intentos: {url}")
                    return None
            except requests.exceptions.HTTPError as e:
                # Errores 5xx: reintento
                if 500 <= e.response.status_code < 600 and attempt < self.max_retries - 1:
                    delay = self.backoff_base ** attempt
                    logger.warning(
                        f"HTTP {e.response.status_code} en {url} (intento {attempt + 1}/{self.max_retries}). "
                        f"Reintentando en {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    # Errores 4xx o último intento de 5xx
                    logger.error(f"Error HTTP {e.response.status_code} al obtener {url}: {e}")
                    return None
            except requests.RequestException as e:
                # Otros errores de red (no recuperables)
                logger.error(f"Error de conexión al obtener {url}: {e}")
                return None

        logger.error(f"Falló tras {self.max_retries} intentos: {url}")
        return None

    def extract_links(self, html: str, base_url: str) -> list[str]:
        """
        Parsea el HTML y extrae todos los enlaces <a> válidos, resolviéndolos en URLs absolutas.
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            # Solo conservamos enlaces HTTP/HTTPS
            if full_url.startswith('http'):
                # Eliminar fragmentos para no reptir página (ej. #seccion)
                full_url = full_url.split('#')[0]
                links.add(full_url)
        return list(links)

    def parse_content(self, html: str, url: str) -> dict:
        """
        Limpia el HTML usando BeautifulSoup, estructura el contenido y valida.
        
        Returns:
            Documento enriquecido con categoría, validez y metadatos.
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Eliminar etiquetas ruidosas
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.extract()

        # Extraer título
        title_tag = soup.find('title')
        title = clean_text(title_tag.get_text()) if title_tag else ""

        # Extraer el contenido principal
        # Las páginas médicas suelen tener <main> o <article>. Si no, caemos en <body>
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        
        content = ""
        if main_content:
            # Separador ' ' evita unir palabras cuando hay etiquetas de bloque adyacentes
            content = clean_text(main_content.get_text(separator=' '))

        doc = {
            "title": title,
            "content": content.lower(),  # Normalización a minúsculas
            "source": self._extract_domain(url),
            "url": url
        }
        
        # Enriquecer documento con validación y categoría
        doc = self.classifier.enrich_document(doc)
        
        return doc

    def _extract_domain(self, url: str) -> str:
        """Extrae el nombre de dominio de una URL."""
        return urlparse(url).netloc
