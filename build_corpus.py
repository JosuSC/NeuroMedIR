import json
import logging
import argparse
import shutil
from pathlib import Path

from crawler.config import DEFAULT_DOMAINS, default_crawl_config
from crawler.crawler import CorpusCrawler

"""
build_corpus.py — Script de construcción del corpus desde cero.

Este es el punto de entrada que usaría cuando quiero poblar el dataset
procesado por primera vez o regenerarlo por completo. Deja bastante claro
qué parámetros están bajo control y cuáles son los valores por defecto.
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def main():
    """Lee parámetros de línea de comandos y ejecuta el crawler principal."""
    parser = argparse.ArgumentParser(description="Build NeuroMedIR bilingual medical corpus")
    parser.add_argument("--max-pages", type=int, default=25000)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.7)
    parser.add_argument("--min-content-chars", type=int, default=600)
    parser.add_argument("--target-valid", type=int, default=2500)
    parser.add_argument("--target-en", type=int, default=0)
    parser.add_argument("--target-es", type=int, default=2500)
    parser.add_argument("--output-dir", type=str, default="data/corpus_v2")
    parser.add_argument("--wipe-processed", action="store_true", help="Borrar los JSON procesados antes de ejecutar el crawler")
    args = parser.parse_args()

    # Arranco desde una configuración base y luego sobreescribo lo que venga por CLI
    config = default_crawl_config()
    config.max_pages = args.max_pages
    config.max_depth = args.max_depth
    config.delay_seconds = args.delay
    config.min_content_chars = args.min_content_chars
    config.min_valid_documents = args.target_valid
     # Solo incluir idiomas con objetivo > 0. Así, al no crawlear inglés,
    # no se exige un target "en" imposible que dejaría el crawler sin parar.
    language_targets = {}
    if args.target_en > 0:
        language_targets["en"] = args.target_en
    if args.target_es > 0:
        language_targets["es"] = args.target_es
    config.language_targets = language_targets
    config.output_dir = Path(args.output_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Opción: borrar los JSON procesados antes de ejecutar (útil para reprocesar desde cero)
    if args.wipe_processed:
        processed_dir = config.output_dir / "processed"
        if processed_dir.exists() and processed_dir.is_dir():
            shutil.rmtree(processed_dir)
            print(f"Directorio 'processed' eliminado: {processed_dir}")

    crawler = CorpusCrawler(config=config, domains=DEFAULT_DOMAINS)
    metrics = crawler.run()

    print("\n=== Corpus Build Summary ===")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
