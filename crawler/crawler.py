"""
crawler.py — Crawler BFS para construir corpus médico bilingüe.

Responsabilidades exclusivas de crawling (NO scraping):
    - Coordinar el flujo BFS de navegación web
    - Respetar robots.txt y políticas de delay entre peticiones
    - Gestionar la cola de URLs (semillas, profundidad, dominios permitidos)
    - Validar calidad de documentos mediante CorpusQualityGate
    - Persistir resultados en disco mediante CorpusStorage
    - Balancear el corpus por idioma (language_targets)

Dependencias:
    - scraper.DomainScraper: Para fetch/parse/extract (inyectado, NO interno)
    - crawler.storage: Para persistencia en disco
    - crawler.quality: Para compuerta de calidad del corpus
    - crawler.language: Para detección de idioma
    - crawler.utils: Para helpers de URLs y logging

Complejidad algorítmica:
    - run():              O(max_paginas * (tiempo_fetch + tiempo_parse + delay))
    - _can_fetch():       O(1) amortizado con caché de robots.txt
    - _is_allowed_domain(): O(dominios_permitidos) por URL verificada
"""

import time
import urllib.robotparser
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Set
from urllib.parse import urlparse

from .config import CrawlConfig, DomainConfig, DEFAULT_DOMAINS
from .language import detect_language, infer_language_from_url
from .quality import CorpusQualityGate
from .storage import CorpusStorage
from .utils import (
    domain_from_url,
    is_http_url,
    normalize_url,
    same_domain_or_subdomain,
    setup_logger,
)

# Antes: from .scraper import DomainScraper  (scraper dentro de crawler — mezcla responsabilidades)
# Ahora: from scraper import DomainScraper   (scraper es módulo independiente)
from ..scraper import DomainScraper

logger = setup_logger(__name__)


@dataclass
class QueueItem:
    """Estructura ligera para representar URLs en la cola del crawler.

    Campos:
        url: URL a procesar.
        depth: Profundidad desde la URL semilla (0 = semilla).
        language_hint: Idioma esperado ("en" o "es").
        source_name: Nombre de la fuente (ej. "PubMed", "MedlinePlus ES").
        category_hint: Categoría esperada (ej. "health_topic").
        domain_scope: Dominio principal de esta rama de crawling.
        allowed_domains: Dominios permitidos para expansión de enlaces.
    """
    url: str
    depth: int
    language_hint: str
    source_name: str
    category_hint: str
    domain_scope: str
    allowed_domains: List[str]


class CorpusCrawler:
    """Crawler orientado a construir un corpus médico bilingüe.

    Flujo principal:
        1. Inicializar cola con URLs semilla por dominio
        2. Para cada URL en la cola:
           a. Verificar si ya fue visitada
           b. Respetar robots.txt
           c. Hacer fetch+parse vía DomainScraper (inyectado)
           d. Validar calidad del documento
           e. Guardar (aceptado o rechazado)
           f. Extraer enlaces y encolar los válidos
        3. Repetir hasta agotar la cola o cumplir objetivos

    NOTA: El scraping (fetch/parse/extract) se delega al módulo scraper/.
    Este módulo SOLO coordina el flujo de crawling BFS.
    """

    def __init__(
        self,
        config: CrawlConfig,
        domains: Optional[List[DomainConfig]] = None,
        scraper: Optional[DomainScraper] = None,
    ):
        """Inicializa el crawler con configuración, dominios y scraper inyectado.

        Args:
            config: Configuración de crawling (delays, depths, targets).
            domains: Lista de configuraciones por dominio (semillas, idioma, etc.).
                     Si es None, usa DEFAULT_DOMAINS del config.
            scraper: DomainScraper inyectado desde el módulo scraper/.
                     Si es None, se crea una instancia nueva con los
                     parámetros del config. La inyección permite tests
                     con scraper mock sin hacer peticiones HTTP reales.
        """
        self.config = config
        self.domains = domains or DEFAULT_DOMAINS
        self.headers = {"User-Agent": config.user_agent}

        # Scraper inyectado: viene del módulo scraper/, no es interno a crawler
        self.scraper = scraper or DomainScraper(
            timeout=config.request_timeout_seconds,
            max_retries=config.max_retries,
            backoff_base_seconds=config.backoff_base_seconds,
        )
        self.storage = CorpusStorage(config.output_dir)
        self.quality = CorpusQualityGate(config.min_content_chars)

        # Estructuras internas del BFS
        self.queue: Deque[QueueItem] = deque()
        self.visited: Set[str] = set()
        self.robot_cache: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}

        # Métricas y resultados en memoria durante la ejecución
        self.valid_docs: List[Dict] = []
        self.rejected_count = 0
        self.next_doc_id = 1
        self.language_counter = Counter()

        # Restaurar estado previo si ya hay documentos en disco
        self._load_existing_state()
        # Poblar la cola con las URLs semilla
        self._bootstrap_queue()

    def _load_existing_state(self):
        """Carga documentos ya procesados para mantener continuidad entre ejecuciones.

        Permite reanudar un crawling interrumpido sin perder el trabajo previo.
        Registra los documentos existentes en la compuerta de calidad para
        evitar aceptar duplicados, y restaura el contador de IDs.
        """
        existing_docs = self.storage.load_existing_documents()
        if not existing_docs:
            return

        max_id = 0
        for doc in existing_docs:
            # Registrar en la compuerta de calidad para evitar duplicados
            self.quality.register_existing(doc)

            # Restaurar contador de idiomas
            lang = doc.get("language")
            if not isinstance(lang, str) or not lang:
                lang = infer_language_from_url(str(doc.get("url", "")))
            if isinstance(lang, str):
                self.language_counter[lang] += 1

            # Restaurar contador de IDs para no colisionar
            doc_id = doc.get("id", 0)
            if isinstance(doc_id, int) and doc_id > max_id:
                max_id = doc_id

        self.next_doc_id = max_id + 1
        logger.info(
            "Estado previo cargado | documentos=%s | por_idioma=%s | proximo_id=%s",
            len(existing_docs),
            dict(self.language_counter),
            self.next_doc_id,
        )

    def _bootstrap_queue(self):
        """Añade las URLs semilla definidas en cada DomainConfig a la cola BFS.

        Cada DomainConfig contiene una lista de semillas que son los puntos
        de partida del crawling para ese dominio.
        """
        for domain_cfg in self.domains:
            for seed in domain_cfg.seeds:
                if not is_http_url(seed):
                    continue
                self.queue.append(
                    QueueItem(
                        url=normalize_url(seed),
                        depth=0,
                        language_hint=domain_cfg.language_hint,
                        source_name=domain_cfg.source_name,
                        category_hint=domain_cfg.category_hint,
                        domain_scope=domain_cfg.domain,
                        allowed_domains=domain_cfg.allowed_domains or [domain_cfg.domain],
                    )
                )

    @staticmethod
    def _is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
        """Verifica si una URL pertenece a la lista de dominios permitidos.

        Comprueba tanto el dominio exacto como subdominios.
        Ej: si allowed_domains=["nih.gov"], acepta "newsinhealth.nih.gov".

        Complejidad: O(d) donde d = número de dominios permitidos.

        Args:
            url: URL a verificar.
            allowed_domains: Lista de dominios permitidos.

        Returns:
            True si la URL pertenece a un dominio permitido.
        """
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return False
        for dominio in allowed_domains:
            d = dominio.lower()
            if host == d or host.endswith(f".{d}"):
                return True
        return False

    def _can_fetch(self, url: str) -> bool:
        """Verifica si el crawler puede acceder a la URL según robots.txt.

        Mantiene un caché de parsers de robots.txt por dominio para no
        descargar el mismo archivo repetidamente.

        Complejidad: O(1) amortizado gracias al caché.

        Args:
            url: URL a verificar.

        Returns:
            True si robots.txt permite el acceso, False si lo prohíbe.
            Si no se puede leer robots.txt, se asume permisivo.
        """
        parsed_domain = domain_from_url(url)
        if not parsed_domain:
            return False

        base = f"https://{parsed_domain}"
        if base not in self.robot_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{base}/robots.txt")
            try:
                rp.read()
                self.robot_cache[base] = rp
            except Exception:
                # Si no se puede leer robots.txt, asumimos permisividad
                # (más seguro para un contexto de investigación académica)
                self.robot_cache[base] = None

        parser = self.robot_cache[base]
        if parser is None:
            return True
        return parser.can_fetch(self.config.user_agent, url)

    def _target_met(self) -> bool:
        """Comprueba si se alcanzaron los objetivos de tamaño e idioma del corpus.

        Returns:
            True si el corpus ya tiene suficientes documentos y balance de idiomas.
        """
        if len(self.valid_docs) < self.config.min_valid_documents:
            return False
        for idioma, objetivo in self.config.language_targets.items():
            if self.language_counter.get(idioma, 0) < objetivo:
                return False
        return True

    def _to_document(self, item: QueueItem, parsed: Dict[str, str], url: str) -> Dict:
        """Convierte el resultado del parser en la estructura de documento persistible.

        Args:
            item: Elemento de la cola con metadatos de la URL.
            parsed: Resultado del scraper con {"title", "content"}.
            url: URL final del documento.

        Returns:
            Diccionario listo para persistir con todos los campos requeridos.
        """
        contenido = parsed.get("content", "")
        idioma = detect_language(contenido, hint=item.language_hint)
        return {
            "id": self.next_doc_id,
            "title": parsed.get("title", ""),
            "content": contenido,
            "source": item.source_name,
            "url": url,
            "category": item.category_hint,
            "language": idioma,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def run(self) -> Dict:
        """Ejecuta el crawling BFS hasta agotar la cola o alcanzar max_pages.

        Flujo por cada URL:
            1. Verificar si ya fue visitada o excede profundidad
            2. Respetar robots.txt
            3. Hacer fetch vía DomainScraper
            4. Validar tipo de contenido (solo text/html)
            5. Parsear contenido vía DomainScraper
            6. Validar calidad del documento
            7. Guardar como aceptado o rechazado
            8. Extraer enlaces y encolar los válidos
            9. Esperar delay entre peticiones

        Returns:
            Métricas del crawling: documentos válidos, rechazados, distribución.
        """
        inicio = time.time()
        paginas_crawleadas = 0

        while self.queue and paginas_crawleadas < self.config.max_pages:
            if self._target_met():
                break

            item = self.queue.popleft()
            url = normalize_url(item.url)

            # Filtros previos al fetch
            if url in self.visited:
                continue
            if item.depth > self.config.max_depth:
                continue
            if not self._can_fetch(url):
                self.visited.add(url)
                continue

            # Fetch vía scraper
            respuesta = self.scraper.fetch(url, headers=self.headers)
            self.visited.add(url)
            paginas_crawleadas += 1

            if respuesta is None:
                self.rejected_count += 1
                self.storage.save_rejected(
                    self.rejected_count,
                    {"url": url, "reason": "fetch_failed"},
                )
                continue

            # Solo procesar contenido HTML
            tipo_contenido = respuesta.headers.get("Content-Type", "")
            if "text/html" not in tipo_contenido:
                self.rejected_count += 1
                self.storage.save_rejected(
                    self.rejected_count,
                    {"url": url, "reason": "non_html_content_type"},
                )
                continue

            html = respuesta.text
            if self.config.save_raw_html:
                self.storage.save_raw(self.next_doc_id, {"url": url, "html": html})

            # Parse y validación
            dominio_fuente = domain_from_url(url)
            parsed = self.scraper.parse_content(html, source_domain=dominio_fuente)
            documento = self._to_document(item, parsed, url)
            calidad = self.quality.validate(documento)

            if calidad.is_valid:
                idioma = documento["language"]

                # Evitar desequilibrar el corpus en un idioma
                if idioma in self.config.language_targets:
                    if self.language_counter[idioma] > self.config.language_targets[idioma] + 100:
                        self.rejected_count += 1
                        self.storage.save_rejected(
                            self.rejected_count,
                            {"url": url, "reason": "language_over_target", "language": idioma},
                        )
                        continue

                # Guardar documento válido
                self.storage.save_processed(self.next_doc_id, documento)
                self.valid_docs.append(documento)
                self.language_counter[idioma] += 1
                self.next_doc_id += 1
            else:
                # Guardar rechazado para auditoría
                self.rejected_count += 1
                payload = dict(documento)
                payload["reason"] = calidad.reason
                self.storage.save_rejected(self.rejected_count, payload)

            # Extraer y encolar enlaces si no se alcanzó la profundidad máxima
            if item.depth < self.config.max_depth:
                enlaces = self.scraper.extract_links(html, base_url=url)
                for enlace in enlaces:
                    enlace_normalizado = normalize_url(enlace)
                    if enlace_normalizado in self.visited:
                        continue
                    if not self._is_allowed_domain(enlace_normalizado, item.allowed_domains):
                        continue

                    self.queue.append(
                        QueueItem(
                            url=enlace_normalizado,
                            depth=item.depth + 1,
                            language_hint=item.language_hint,
                            source_name=item.source_name,
                            category_hint=item.category_hint,
                            domain_scope=item.domain_scope,
                            allowed_domains=item.allowed_domains,
                        )
                    )

            # Respetar delay entre peticiones
            time.sleep(self.config.delay_seconds)

        # Calcular métricas finales
        fin = time.time()
        todos_docs = self.storage.load_existing_documents()
        metricas = self.storage.write_metrics(
            valid_docs=todos_docs,
            rejected_count=self.rejected_count,
            started_at=inicio,
            finished_at=fin,
        )

        logger.info(
            "Crawling completado | validos=%s | rechazados=%s | por_idioma=%s",
            metricas["total_valid_documents"],
            metricas["total_rejected_documents"],
            metricas["distribution_by_language"],
        )
        return metricas