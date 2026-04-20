import json
import logging
import argparse
from pathlib import Path

from crawler.config import DEFAULT_DOMAINS, default_crawl_config
from crawler.crawler import CorpusCrawler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Build NeuroMedIR bilingual medical corpus")
    parser.add_argument("--max-pages", type=int, default=20000)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--min-content-chars", type=int, default=600)
    parser.add_argument("--target-valid", type=int, default=2000)
    parser.add_argument("--target-en", type=int, default=1200)
    parser.add_argument("--target-es", type=int, default=800)
    parser.add_argument("--output-dir", type=str, default="data/corpus_v2")
    args = parser.parse_args()

    config = default_crawl_config()
    config.max_pages = args.max_pages
    config.max_depth = args.max_depth
    config.delay_seconds = args.delay
    config.min_content_chars = args.min_content_chars
    config.min_valid_documents = args.target_valid
    config.language_targets = {"en": args.target_en, "es": args.target_es}
    config.output_dir = Path(args.output_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    crawler = CorpusCrawler(config=config, domains=DEFAULT_DOMAINS)
    metrics = crawler.run()

    print("\n=== Corpus Build Summary ===")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
