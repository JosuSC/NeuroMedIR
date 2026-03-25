import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .utils import clean_text, setup_logger

logger = setup_logger(__name__)

class Scraper:
    def fetch_page(self, url: str, headers: dict, timeout: int = 10) -> requests.Response:
        """
        Hace un GET request a la URL dada.
        Retorna el objeto Response si fue exitoso, None si falla (HTTP errors, timeouts).
        """
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()  # Lanza excepción para códigos 4xx/5xx
            return response
        except requests.RequestException as e:
            logger.error(f"Error HTTP o de conexión al obtener {url}: {e}")
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
        Limpia el HTML usando BeautifulSoup y estructura el contenido.
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

        return {
            "title": title,
            "content": content.lower(),  # Normalización a minúsculas
            "source": self._extract_domain(url),
            "url": url
        }

    def _extract_domain(self, url: str) -> str:
        """Extrae el nombre de dominio de una URL."""
        return urlparse(url).netloc
