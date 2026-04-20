import hashlib
import logging
import re
from urllib.parse import urlparse, urlunparse


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") if parsed.path not in ("", "/") else "/"
    query = parsed.query
    return urlunparse((scheme, netloc, path, "", query, ""))


def is_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def domain_from_url(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def same_domain_or_subdomain(url: str, domain: str) -> bool:
    host = domain_from_url(url)
    if not host:
        return False
    return host == domain or host.endswith(f".{domain}")


def strip_noise(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def text_fingerprint(text: str) -> str:
    normalized = re.sub(r"\W+", " ", (text or "").lower()).strip()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()
