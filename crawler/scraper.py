import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .utils import strip_noise


DOMAIN_SELECTORS = {
    "pubmed.ncbi.nlm.nih.gov": ["main", "article", "section.abstract", "div.abstract-content"],
    "medlineplus.gov": ["main", "article", "#topic-summary", "body"],
    "who.int": ["main", "article", "div.sf_colsIn", "body"],
    "nih.gov": ["main", "article", "div.article-content", "body"],
    "scielo.org": ["main", "article", "#articleText", "body"],
}


class DomainScraper:
    def __init__(self, timeout: int = 15, max_retries: int = 3, backoff_base_seconds: float = 1.8):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds

    def fetch(self, url: str, headers: Dict[str, str]) -> Optional[requests.Response]:
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
        soup = BeautifulSoup(html, "html.parser")

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
