"""
crawler.py — Crawler BFS PARALELO para construir corpus médico.

Cambio principal respecto a la versión anterior:
    - Antes: un solo hilo, cola global, time.sleep() global de 1s por página.
      Resultado: ~1 página/segundo en TODO el sistema (delay en serie).
    - Ahora: un hilo por dominio (ThreadPoolExecutor). Cada dominio corre su
      propio BFS aislado y respeta su propio delay de cortesía. Los N dominios
      avanzan en paralelo → throughput ~N veces mayor sin maltratar ningún
      servidor individual.

Por qué hilos y no procesos:
    - El crawling es I/O-bound: las peticiones de red liberan el GIL, así que
      los hilos dan paralelismo real para la parte cara (esperar la red).
    - Estado compartido coordinado en un solo lugar: dedup global (URLs y
      fingerprints), contador de doc_id atómico, balance de idioma y objetivos
      del corpus. Con procesos separados habría que fusionar corpus al final.
    - El resume (cargar estado previo de disco) sigue funcionando igual.

Aislamiento por dominio:
    El BFS nunca cruza de un dominio a otro porque _is_allowed_domain filtra
    los enlaces por allowed_domains. Por eso cada DomainConfig se puede ejecutar
    como un crawler independiente sin pisarse con los demás.

Seguridad de hilos:
    - Estado compartido (quality gate, contadores, valid_docs, next_doc_id,
      rejected_count, pages_crawled) protegido por un único lock.
    - visited y robots_cache son LOCALES a cada hilo (cada dominio solo se
      visita a sí mismo), así que no necesitan lock.
    - Cada hilo usa su propia instancia de scraper (requests.Session no es
      thread-safe para uso concurrente).
"""

import time
import threading
import urllib.robotparser
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
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
    setup_logger,
)

from scraper import DomainScraper
from .url_filters import should_skip_url

logger = setup_logger(__name__)


@dataclass
class QueueItem:
    """URL pendiente dentro del BFS de un dominio."""
    url: str
    depth: int
    language_hint: str
    source_name: str
    category_hint: str
    domain_scope: str
    allowed_domains: List[str]


class CorpusCrawler:
    """Crawler paralelo (un hilo por dominio) para corpus médico.

    Interfaz pública sin cambios: CorpusCrawler(config, domains, scraper).run()
    devuelve el mismo diccionario de métricas que la versión secuencial, para
    que build_corpus.py no necesite modificaciones.
    """

    def __init__(
        self,
        config: CrawlConfig,
        domains: Optional[List[DomainConfig]] = None,
        scraper: Optional[DomainScraper] = None,
        max_workers: Optional[int] = None,
    ):
        """
        Args:
            config: Configuración de crawling (delays, depths, targets).
            domains: Configuraciones por dominio. Si es None usa DEFAULT_DOMAINS.
            scraper: Scraper inyectado. Si se pasa, se COMPARTE entre hilos
                     (úsalo solo en tests con un mock). En producción déjalo en
                     None: cada hilo crea su propia instancia (thread-safe).
            max_workers: Nº máximo de hilos concurrentes. Por defecto, uno por
                         dominio (acotado a 16).
        """
        self.config = config
        self.domains = domains or DEFAULT_DOMAINS
        self.headers = {"User-Agent": config.user_agent}

        # Si inyectan un scraper (tests), se comparte. Si no, cada hilo crea
        # el suyo con la factory.
        self._shared_scraper = scraper
        self.storage = CorpusStorage(config.output_dir)
        self.quality = CorpusQualityGate(config.min_content_chars)

        self.max_workers = max_workers or min(len(self.domains), 16)

        # ---- Estado compartido entre hilos (protegido por _lock) ----
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.valid_docs: List[Dict] = []
        self.rejected_count = 0
        self.next_doc_id = 1
        self.language_counter: Counter = Counter()
        self.pages_crawled = 0

        self._load_existing_state()

    # =========================================================================
    # Factory de scraper por hilo
    # =========================================================================

    def _new_scraper(self) -> DomainScraper:
        """Devuelve el scraper compartido (tests) o crea uno nuevo por hilo."""
        if self._shared_scraper is not None:
            return self._shared_scraper
        return DomainScraper(
            timeout=self.config.request_timeout_seconds,
            max_retries=self.config.max_retries,
            backoff_base_seconds=self.config.backoff_base_seconds,
        )

    # =========================================================================
    # Resume: cargar estado previo de disco
    # =========================================================================

    def _load_existing_state(self):
        """Carga documentos ya procesados para reanudar sin perder trabajo."""
        existing_docs = self.storage.load_existing_documents()
        if not existing_docs:
            return

        max_id = 0
        for doc in existing_docs:
            self.quality.register_existing(doc)

            lang = doc.get("language")
            if not isinstance(lang, str) or not lang:
                lang = infer_language_from_url(str(doc.get("url", "")))
            if isinstance(lang, str):
                self.language_counter[lang] += 1

            doc_id = doc.get("id", 0)
            if isinstance(doc_id, int) and doc_id > max_id:
                max_id = doc_id

        self.next_doc_id = max_id + 1
        logger.info(
            "Estado previo cargado | documentos=%s | por_idioma=%s | proximo_id=%s",
            len(existing_docs), dict(self.language_counter), self.next_doc_id,
        )

    # =========================================================================
    # Helpers de dominio / robots
    # =========================================================================

    @staticmethod
    def _is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
        """True si la URL pertenece a un dominio permitido o a un subdominio."""
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return False
        for dominio in allowed_domains:
            d = dominio.lower()
            if host == d or host.endswith(f".{d}"):
                return True
        return False

    def _can_fetch(self, url: str, robot_cache: dict) -> bool:
        """Verifica robots.txt usando un caché LOCAL del hilo (sin lock)."""
        parsed_domain = domain_from_url(url)
        if not parsed_domain:
            return False

        base = f"https://{parsed_domain}"
        if base not in robot_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{base}/robots.txt")
            try:
                rp.read()
                robot_cache[base] = rp
            except Exception:
                robot_cache[base] = None

        parser = robot_cache[base]
        if parser is None:
            return True
        return parser.can_fetch(self.config.user_agent, url)

    # =========================================================================
    # Objetivos del corpus (se llaman con el lock tomado)
    # =========================================================================

    def _target_met_locked(self) -> bool:
        """True si ya se alcanzaron tamaño y balance de idioma. Asume lock."""
        if len(self.valid_docs) < self.config.min_valid_documents:
            return False
        for idioma, objetivo in self.config.language_targets.items():
            if self.language_counter.get(idioma, 0) < objetivo:
                return False
        return True

    def _to_document(self, item: QueueItem, parsed: Dict[str, str], url: str) -> Dict:
        """Convierte el parseo en documento (sin asignar id todavía)."""
        contenido = parsed.get("content", "")
        idioma = detect_language(contenido, hint=item.language_hint)
        return {
            "title": parsed.get("title", ""),
            "content": contenido,
            "source": item.source_name,
            "url": url,
            "category": item.category_hint,
            "language": idioma,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    # =========================================================================
    # Registro thread-safe de resultados
    # =========================================================================

    def _register_valid(self, documento: Dict) -> bool:
        """Valida, asigna id y persiste un documento. Devuelve True si se aceptó.

        Toda la sección crítica (validación con dedup + asignación de id +
        actualización de contadores) ocurre bajo el lock para evitar carreras.
        """
        with self._lock:
            if self._stop.is_set():
                return False

            calidad = self.quality.validate(documento)
            if not calidad.is_valid:
                self.rejected_count += 1
                idx = self.rejected_count
                payload = dict(documento)
                payload["reason"] = calidad.reason
                # El guardado a disco puede salir del lock, pero es barato; lo
                # dejamos dentro para no complicar el manejo de índices.
                self.storage.save_rejected(idx, payload)
                return False

            idioma = documento["language"]
            if idioma in self.config.language_targets:
                if self.language_counter[idioma] > self.config.language_targets[idioma] + 100:
                    self.rejected_count += 1
                    idx = self.rejected_count
                    payload = dict(documento)
                    payload["reason"] = "language_over_target"
                    self.storage.save_rejected(idx, payload)
                    return False

            doc_id = self.next_doc_id
            self.next_doc_id += 1
            documento["id"] = doc_id
            self.storage.save_processed(doc_id, documento)
            self.valid_docs.append(documento)
            self.language_counter[idioma] += 1

            if self._target_met_locked():
                self._stop.set()
            return True

    def _register_fetch_failure(self, url: str, reason: str):
        with self._lock:
            self.rejected_count += 1
            idx = self.rejected_count
        self.storage.save_rejected(idx, {"url": url, "reason": reason})

    # =========================================================================
    # Worker: BFS de un solo dominio
    # =========================================================================

    def _crawl_domain(self, domain_cfg: DomainConfig):
        """Ejecuta el BFS completo de un dominio en su propio hilo."""
        scraper = self._new_scraper()
        visited: Set[str] = set()
        robot_cache: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}

        queue: Deque[QueueItem] = deque()
        for seed in domain_cfg.seeds:
            if is_http_url(seed):
                queue.append(QueueItem(
                    url=normalize_url(seed),
                    depth=0,
                    language_hint=domain_cfg.language_hint,
                    source_name=domain_cfg.source_name,
                    category_hint=domain_cfg.category_hint,
                    domain_scope=domain_cfg.domain,
                    allowed_domains=domain_cfg.allowed_domains or [domain_cfg.domain],
                ))

        logger.info("[%s] iniciando (%s semillas)", domain_cfg.source_name, len(queue))

        while queue:
            if self._stop.is_set():
                break

            # Tope global de páginas (lectura/escritura atómica)
            with self._lock:
                if self.pages_crawled >= self.config.max_pages:
                    self._stop.set()
                    break

            item = queue.popleft()
            url = normalize_url(item.url)

            if url in visited:
                continue
            if item.depth > self.config.max_depth:
                continue
            if not self._can_fetch(url, robot_cache):
                visited.add(url)
                continue
            if should_skip_url(url):
                visited.add(url)
                continue

            respuesta = scraper.fetch(url, headers=self.headers)
            visited.add(url)
            with self._lock:
                self.pages_crawled += 1

            if respuesta is None:
                self._register_fetch_failure(url, "fetch_failed")
                time.sleep(self.config.delay_seconds)
                continue

            tipo_contenido = respuesta.headers.get("Content-Type", "")
            if "text/html" not in tipo_contenido:
                self._register_fetch_failure(url, "non_html_content_type")
                time.sleep(self.config.delay_seconds)
                continue

            html_bytes = respuesta.content
            if self.config.save_raw_html:
                decode_enc = respuesta.encoding or getattr(respuesta, "apparent_encoding", None) or "utf-8"
                try:
                    decoded = html_bytes.decode(decode_enc, errors="replace")
                except Exception:
                    decoded = html_bytes.decode("utf-8", errors="replace")
                # next_doc_id puede cambiar entre hilos; el raw es solo auxiliar
                self.storage.save_raw(self.next_doc_id, {"url": url, "html": decoded})

            dominio_fuente = domain_from_url(url)
            parsed = scraper.parse_content(html_bytes, source_domain=dominio_fuente)
            documento = self._to_document(item, parsed, url)
            self._register_valid(documento)

            # Encolar enlaces del mismo dominio
            if item.depth < self.config.max_depth:
                enlaces = scraper.extract_links(html_bytes, base_url=url)
                for enlace in enlaces:
                    enlace_normalizado = normalize_url(enlace)
                    if enlace_normalizado in visited:
                        continue
                    if not self._is_allowed_domain(enlace_normalizado, item.allowed_domains):
                        continue
                    if should_skip_url(enlace_normalizado):
                        continue
                    queue.append(QueueItem(
                        url=enlace_normalizado,
                        depth=item.depth + 1,
                        language_hint=item.language_hint,
                        source_name=item.source_name,
                        category_hint=item.category_hint,
                        domain_scope=item.domain_scope,
                        allowed_domains=item.allowed_domains,
                    ))

            # Cortesía: este delay es POR DOMINIO (cada hilo espera a su propio
            # servidor). Los demás dominios siguen avanzando en paralelo.
            time.sleep(self.config.delay_seconds)

        logger.info("[%s] terminado", domain_cfg.source_name)

    # =========================================================================
    # Orquestación paralela
    # =========================================================================

    def run(self) -> Dict:
        """Lanza un hilo por dominio y espera a que todos terminen."""
        inicio = time.time()
        logger.info(
            "Crawling paralelo | dominios=%s | workers=%s | delay/dominio=%ss",
            len(self.domains), self.max_workers, self.config.delay_seconds,
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._crawl_domain, d) for d in self.domains]
            for f in futures:
                try:
                    f.result()
                except Exception as e:
                    logger.error("Worker de dominio falló: %s", e)

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