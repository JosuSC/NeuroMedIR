import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .utils import setup_logger
from .language import infer_language_from_url

logger = setup_logger(__name__)


class CorpusStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.rejected_dir = self.base_dir / "rejected"
        self.metrics_path = self.base_dir / "corpus_metrics.json"

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.rejected_dir.mkdir(parents=True, exist_ok=True)

    def load_existing_documents(self) -> List[Dict]:
        docs = []
        if not self.processed_dir.exists():
            return docs

        for path in self.processed_dir.rglob("*.json"):
            if not path.is_file():
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    docs.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                logger.warning("Skipping unreadable processed document: %s", path)
        return docs

    def save_raw(self, doc_id: int, payload: Dict):
        path = self.raw_dir / f"doc_{doc_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def save_processed(self, doc_id: int, payload: Dict):
        lang = payload["language"]
        category = payload["category"]
        out_dir = self.processed_dir / lang / category
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"doc_{doc_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def save_rejected(self, idx: int, payload: Dict):
        path = self.rejected_dir / f"rejected_{idx}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def write_metrics(self, valid_docs: List[Dict], rejected_count: int, started_at: float, finished_at: float):
        by_lang = Counter(
            d.get("language") or infer_language_from_url(str(d.get("url", "")))
            for d in valid_docs
        )
        by_source = Counter(d.get("source", "unknown") for d in valid_docs)
        by_category = Counter(d.get("category", "unknown") for d in valid_docs)

        avg_content_len = 0.0
        if valid_docs:
            avg_content_len = sum(len(str(d.get("content", ""))) for d in valid_docs) / len(valid_docs)

        metrics = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_valid_documents": len(valid_docs),
            "total_rejected_documents": rejected_count,
            "validity_ratio": round(len(valid_docs) / max(1, len(valid_docs) + rejected_count), 4),
            "distribution_by_language": dict(by_lang),
            "distribution_by_source": dict(by_source),
            "distribution_by_category": dict(by_category),
            "average_content_length_chars": round(avg_content_len, 2),
            "crawl_duration_seconds": round(finished_at - started_at, 2),
            "docs_per_minute": round((len(valid_docs) / max(1e-6, (finished_at - started_at))) * 60, 2),
            "examples": valid_docs[:5],
        }

        with self.metrics_path.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

        logger.info("Metrics written to %s", self.metrics_path)
        return metrics
