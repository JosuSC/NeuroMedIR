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
from .scraper import DomainScraper
from .storage import CorpusStorage
from .utils import (
    domain_from_url,
    is_http_url,
    normalize_url,
    same_domain_or_subdomain,
    setup_logger,
)

logger = setup_logger(__name__)


@dataclass
class QueueItem:
    url: str
    depth: int
    language_hint: str
    source_name: str
    category_hint: str
    domain_scope: str
    allowed_domains: List[str]


class CorpusCrawler:
    def __init__(self, config: CrawlConfig, domains: Optional[List[DomainConfig]] = None):
        self.config = config
        self.domains = domains or DEFAULT_DOMAINS
        self.headers = {"User-Agent": config.user_agent}

        self.scraper = DomainScraper(
            timeout=config.request_timeout_seconds,
            max_retries=config.max_retries,
            backoff_base_seconds=config.backoff_base_seconds,
        )
        self.storage = CorpusStorage(config.output_dir)
        self.quality = CorpusQualityGate(config.min_content_chars)

        self.queue: Deque[QueueItem] = deque()
        self.visited: Set[str] = set()
        self.robot_cache: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}

        self.valid_docs: List[Dict] = []
        self.rejected_count = 0
        self.next_doc_id = 1
        self.language_counter = Counter()

        self._load_existing_state()
        self._bootstrap_queue()

    def _load_existing_state(self):
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
            "Loaded existing corpus state | docs=%s | by_lang=%s | next_id=%s",
            len(existing_docs),
            dict(self.language_counter),
            self.next_doc_id,
        )

    def _bootstrap_queue(self):
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
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return False
        for domain in allowed_domains:
            d = domain.lower()
            if host == d or host.endswith(f".{d}"):
                return True
        return False

    def _can_fetch(self, url: str) -> bool:
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
                self.robot_cache[base] = None

        parser = self.robot_cache[base]
        if parser is None:
            return True
        return parser.can_fetch(self.config.user_agent, url)

    def _target_met(self) -> bool:
        if len(self.valid_docs) < self.config.min_valid_documents:
            return False
        for lang, target in self.config.language_targets.items():
            if self.language_counter.get(lang, 0) < target:
                return False
        return True

    def _to_document(self, item: QueueItem, parsed: Dict[str, str], url: str) -> Dict:
        content = parsed.get("content", "")
        lang = detect_language(content, hint=item.language_hint)
        return {
            "id": self.next_doc_id,
            "title": parsed.get("title", ""),
            "content": content,
            "source": item.source_name,
            "url": url,
            "category": item.category_hint,
            "language": lang,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def run(self) -> Dict:
        started = time.time()
        crawled_pages = 0

        while self.queue and crawled_pages < self.config.max_pages:
            if self._target_met():
                break

            item = self.queue.popleft()
            url = normalize_url(item.url)

            if url in self.visited:
                continue
            if item.depth > self.config.max_depth:
                continue
            if not self._can_fetch(url):
                self.visited.add(url)
                continue

            response = self.scraper.fetch(url, headers=self.headers)
            self.visited.add(url)
            crawled_pages += 1

            if response is None:
                self.rejected_count += 1
                self.storage.save_rejected(
                    self.rejected_count,
                    {"url": url, "reason": "fetch_failed"},
                )
                continue

            ctype = response.headers.get("Content-Type", "")
            if "text/html" not in ctype:
                self.rejected_count += 1
                self.storage.save_rejected(
                    self.rejected_count,
                    {"url": url, "reason": "non_html_content_type"},
                )
                continue

            html = response.text
            if self.config.save_raw_html:
                self.storage.save_raw(self.next_doc_id, {"url": url, "html": html})

            source_domain = domain_from_url(url)
            parsed = self.scraper.parse_content(html, source_domain=source_domain)
            document = self._to_document(item, parsed, url)
            quality = self.quality.validate(document)

            if quality.is_valid:
                lang = document["language"]
                if lang in self.config.language_targets:
                    # Avoid creating an imbalanced corpus far above target for one language.
                    if self.language_counter[lang] > self.config.language_targets[lang] + 100:
                        self.rejected_count += 1
                        self.storage.save_rejected(
                            self.rejected_count,
                            {"url": url, "reason": "language_over_target", "language": lang},
                        )
                        continue

                self.storage.save_processed(self.next_doc_id, document)
                self.valid_docs.append(document)
                self.language_counter[lang] += 1
                self.next_doc_id += 1
            else:
                self.rejected_count += 1
                payload = dict(document)
                payload["reason"] = quality.reason
                self.storage.save_rejected(self.rejected_count, payload)

            if item.depth < self.config.max_depth:
                links = self.scraper.extract_links(html, base_url=url)
                for link in links:
                    normalized_link = normalize_url(link)
                    if normalized_link in self.visited:
                        continue
                    if not self._is_allowed_domain(normalized_link, item.allowed_domains):
                        continue

                    self.queue.append(
                        QueueItem(
                            url=normalized_link,
                            depth=item.depth + 1,
                            language_hint=item.language_hint,
                            source_name=item.source_name,
                            category_hint=item.category_hint,
                            domain_scope=item.domain_scope,
                            allowed_domains=item.allowed_domains,
                        )
                    )

            time.sleep(self.config.delay_seconds)

        finished = time.time()
        all_docs = self.storage.load_existing_documents()
        metrics = self.storage.write_metrics(
            valid_docs=all_docs,
            rejected_count=self.rejected_count,
            started_at=started,
            finished_at=finished,
        )

        logger.info(
            "Corpus build complete | valid=%s | rejected=%s | by_lang=%s",
            metrics["total_valid_documents"],
            metrics["total_rejected_documents"],
            metrics["distribution_by_language"],
        )
        return metrics
