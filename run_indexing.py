import json
import logging
from pathlib import Path
from indexing.indexer import Indexer
from indexing.configs import settings as idx_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("=== NeuroMedIR: Re-Indexación Masiva de Todos los Documentos ===")
    logger.info("=" * 60)

    # 1. Buscar todos los documentos guardados en corpus_v2/processed
    processed_dir = idx_settings.PROCESSED_DATA_DIR
    logger.info(f"Leyendo documentos desde: {processed_dir}")

    if not processed_dir.exists():
        logger.error(f"El directorio no existe: {processed_dir}")
        return

    documents = []
    errors = 0
    for filepath in processed_dir.rglob("*.json"):
        if not filepath.is_file():
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                doc = json.load(f)
            if "id" in doc and "content" in doc:
                documents.append(doc)
            else:
                logger.warning(f"Documento incompleto ignorado: {filepath}")
        except Exception as e:
            logger.error(f"Fallo al leer {filepath}: {e}")
            errors += 1

    logger.info(f"Total documentos encontrados: {len(documents)} ({errors} errores al leer)")

    if not documents:
        logger.warning("No hay documentos para indexar. Ejecuta build_corpus.py primero.")
        return

    # 2. Inicializar el Indexer
    indexer = Indexer()

    # 3. Indexar (BM25 y FAISS)
    logger.info("Iniciando indexación (esto puede tomar varios minutos debido a los Embeddings FAISS)...")
    indexer.index_documents(documents)

    # 4. Guardar
    logger.info("Guardando índices en disco...")
    indexer.save_indices()
    
    logger.info("✅ Indexación Masiva Finalizada con Éxito.")

if __name__ == "__main__":
    main()
