import time
import urllib.robotparser
from urllib.parse import urlparse
from typing import List, Set
from queue import Queue

from .scraper import Scraper
from .storage import Storage
from .utils import setup_logger, is_valid_url

logger = setup_logger(__name__)

class Crawler:
    def __init__(
        self, 
        seed_urls: List[str], 
        max_pages: int = 100, 
        max_depth: int = 2,
        delay_seconds: float = 1.0,
        user_agent: str = "NeuroMedIR-Bot/1.0 (+http://localhost)"
    ):
        self.seed_urls = seed_urls
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay_seconds = delay_seconds
        self.user_agent = user_agent
        self.headers = {'User-Agent': self.user_agent}

        self.scraper = Scraper()
        self.storage = Storage()
        
        self.visited_urls: Set[str] = set()
        # Cola para BFS: almacena tuplas (url, profundidad_actual)
        self.queue: Queue = Queue()
        
        self.documents_crawled = 0
        self.robot_parsers = {}

    def _can_fetch(self, url: str) -> bool:
        """Verifica el archivo robots.txt del dominio para decidir si podemos visitarlo."""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if base_url not in self.robot_parsers:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{base_url}/robots.txt")
            try:
                rp.read()
                self.robot_parsers[base_url] = rp
            except Exception as e:
                logger.warning(f"No se pudo procesar robots.txt para {base_url}: {e}")
                self.robot_parsers[base_url] = None
        
        rp = self.robot_parsers[base_url]
        if rp:
            # Usar * si el User-Agent específico no devuelve info real,
            # pero por estándar pasamos el user-agent exacto.
            return rp.can_fetch(self.user_agent, url)
        return True  # Si no pudimos leer robots.txt, procedemos por defecto

    def _same_domain(self, target_url: str, seed_url: str) -> bool:
        """Asegura que no nos salgamos del dominio médico original si no lo deseamos."""
        return urlparse(target_url).netloc == urlparse(seed_url).netloc

    def start(self):
        """Inicia el ciclo principal del crawler."""
        logger.info(f"Iniciando crawler con seeds: {self.seed_urls}")
        
        for url in self.seed_urls:
            if is_valid_url(url):
                self.queue.put((url, 0))

        while not self.queue.empty() and self.documents_crawled < self.max_pages:
            current_url, depth = self.queue.get()

            if current_url in self.visited_urls:
                continue
                
            if depth > self.max_depth:
                continue

            if not self._can_fetch(current_url):
                logger.info(f"Bloqueado por robots.txt: {current_url}")
                self.visited_urls.add(current_url)
                continue

            logger.info(f"Crawleando ({self.documents_crawled + 1}/{self.max_pages}) [Depth {depth}]: {current_url}")
            
            response = self.scraper.fetch_page(current_url, self.headers)
            
            if response and 'text/html' in response.headers.get('Content-Type', ''):
                html_content = response.text
                
                # Extracción y parsing
                parsed_data = self.scraper.parse_content(html_content, current_url)
                
                # Filtrar páginas muy vacías (ej., puro boilerplate o error)
                if len(parsed_data["content"]) > 150:
                    doc_id = self.documents_crawled + 1
                    parsed_data["id"] = doc_id
                    
                    # Guardamos el JSON procesado
                    self.storage.save_processed(doc_id, parsed_data)
                    self.documents_crawled += 1
                
                # Descubrir y encolar nuevos enlaces si no hemos llegado a límite de profundidad
                if depth < self.max_depth:
                    links = self.scraper.extract_links(html_content, current_url)
                    for link in links:
                        # Política: evitar link farms externos comprobando dominio común,
                        # o relajalo si quieres crawls a otros sitios
                        if self._same_domain(link, current_url) and link not in self.visited_urls:
                             self.queue.put((link, depth + 1))
            
            # Marcamos URL como visitada
            self.visited_urls.add(current_url)
            
            # Cortesía (Polite crawling)
            time.sleep(self.delay_seconds)

        logger.info(f"Crawling finalizado. Documentos recolectados: {self.documents_crawled}")
