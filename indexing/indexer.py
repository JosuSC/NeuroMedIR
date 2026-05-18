import logging
import time
from typing import List, Dict

from .configs import settings
from .preprocess.text_cleaner import TextCleaner
from .lexical_index.bm25_index import BM25Index
from .vector_index.faiss_hnsw import FAISSHNSWIndex
from .multimodal.text_encoder import TextEncoder
from .storage.index_io import IndexStorage

logger = logging.getLogger(__name__)


class Indexer:
    """Fachada de indexación (BM25 + FAISS) con comentarios en tono humano.

    Propósito: centralizar la construcción y la actualización incremental de
    los índices léxicos y semánticos. Mantengo métodos separados para
    indexar lotes grandes (`index_documents`) y para agregar documentos
    dinámicos (`add_documents`) usados por la expansión en tiempo real.
    """

    def __init__(self):
        # Utiles para limpieza y encoding
        self.cleaner = TextCleaner()
        self.encoder = TextEncoder(
            settings.EMBEDDING_MODEL_NAME,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
        )
        # mapping doc_id -> texto semántico (útil para persistencia y RAG futuro)
        self.semantic_doc_texts = {}
        
        # Índices principales: léxico (BM25) y vectorial (FAISS HNSW)
        self.lexical_index = BM25Index(k1=settings.BM25_PARAMS["k1"], b=settings.BM25_PARAMS["b"])
        self.semantic_index = FAISSHNSWIndex(
            dimension=settings.EMBEDDING_DIM,
            m=settings.HNSW_M,
            ef_construction=settings.HNSW_EF_CONSTRUCTION
        )
        self.storage = IndexStorage(str(settings.INDEX_STORAGE_DIR))

    def index_documents(self, documents: List[Dict]):
        """Indexa un lote de documentos desde cero.

        Expectativas del input: cada `doc` debe ser un dict con `id`, `title` y `content`.
        Proceso: valida, preprocesa para BM25, preprocesa para embeddings, genera
        embeddings por batch y construye ambos índices.
        """
        if not isinstance(documents, list):
            raise TypeError("documents must be a list of dictionaries")

        t_start = time.perf_counter()
        logger.info(f"Indexing {len(documents)} documents...")
        doc_ids = []
        tokenized_corpus = []
        texts_for_semantic = []
        self.semantic_doc_texts = {}
        seen_ids = set()
        skipped_invalid = 0
        skipped_empty = 0

        for idx, doc in enumerate(documents, start=1):
            # Validaciones simples para evitar corruptos
            if not isinstance(doc, dict):
                skipped_invalid += 1
                logger.warning(f"Skipping document #{idx}: expected dict, got {type(doc)}")
                continue

            doc_id = doc.get("id")
            title = doc.get("title", "")
            content = doc.get("content", "")

            if doc_id is None or not isinstance(title, str) or not isinstance(content, str):
                skipped_invalid += 1
                logger.warning(
                    f"Skipping document #{idx}: invalid schema (id/title/content required)."
                )
                continue

            if doc_id in seen_ids:
                skipped_invalid += 1
                logger.warning(f"Skipping duplicate document id: {doc_id}")
                continue

            # Combino título y contenido: da más contexto a embeddings y BM25
            raw_text = f"{title}. {content}"
            
            # 1) Tokens para BM25
            tokens = self.cleaner.preprocess_for_lexical(raw_text)
            
            # 2) Texto limpio para embeddings
            semantic_text = self.cleaner.preprocess_for_semantic(raw_text)

            if not tokens and not semantic_text.strip():
                skipped_empty += 1
                logger.warning(f"Skipping empty document after preprocessing: id={doc_id}")
                continue
            
            seen_ids.add(doc_id)
            doc_ids.append(doc_id)
            tokenized_corpus.append(tokens)
            texts_for_semantic.append(semantic_text)
            self.semantic_doc_texts[doc_id] = semantic_text

        if not doc_ids:
            raise ValueError("No valid documents available after validation/preprocessing.")
            
        # Construcción del índice léxico
        logger.info("Building lexical index (BM25)...")
        self.lexical_index.build_index(tokenized_corpus, doc_ids)
        
        # Generación de embeddings y construcción del índice semántico
        logger.info("Generating embeddings and building semantic index (FAISS HNSW)...")
        embeddings = self.encoder.encode(texts_for_semantic)
        self.semantic_index.build_index(embeddings, doc_ids)

        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            f"Indexing complete. Indexed: {len(doc_ids)} | "
            f"Skipped invalid: {skipped_invalid} | Skipped empty: {skipped_empty} | "
            f"Total time: {elapsed_ms:.1f}ms"
        )

    def add_documents(self, documents: List[Dict]):
        """Agrega documentos de forma incremental a índices ya existentes.

        Uso típico: integración de resultados de `dynamic_expansion` en caliente.
        """
        if not isinstance(documents, list) or not documents:
            return

        logger.info(f"Adding {len(documents)} new documents to indices...")
        
        new_ids = []
        new_tokens = []
        new_semantic_texts = []
        
        for doc in documents:
            doc_id = doc.get("id")
            title = doc.get("title", "")
            content = doc.get("content", "")
            if doc_id is None or not title or not content:
                continue
                
            raw_text = f"{title}. {content}"
            tokens = self.cleaner.preprocess_for_lexical(raw_text)
            semantic_text = self.cleaner.preprocess_for_semantic(raw_text)
            
            if tokens and semantic_text.strip():
                new_ids.append(doc_id)
                new_tokens.append(tokens)
                new_semantic_texts.append(semantic_text)
                self.semantic_doc_texts[doc_id] = semantic_text
        
        if not new_ids:
            return

        # Actualizo BM25 en memoria
        self.lexical_index.add_documents(new_tokens, new_ids)
        
        # Calculo embeddings y añado a FAISS
        embeddings = self.encoder.encode(new_semantic_texts)
        self.semantic_index.add_embeddings(embeddings, new_ids)
        
        # Persisto los cambios para que sobrevivan a reinicios
        self.save_indices()
        logger.info(f"Successfully added and saved {len(new_ids)} new documents to indices.")

    def search_lexical(self, query: str, top_k: int = 10) -> List[Dict]:
        """Busca por palabras clave usando BM25.

        Retorna una lista de dicts {'doc_id', 'score'}.
        """
        query_tokens = self.cleaner.preprocess_for_lexical(query)
        if not query_tokens:
            return []
        return self.lexical_index.search(query_tokens, top_k)

    def search_semantic(self, query: str, top_k: int = 10) -> List[Dict]:
        """Busca semánticamente: limpio la query y obtengo vecinos en FAISS."""
        clean_query = self.cleaner.preprocess_for_semantic(query)
        if not clean_query:
            return []
        query_embedding = self.encoder.encode([clean_query])[0]
        return self.semantic_index.search(query_embedding, top_k, ef_search=settings.HNSW_EF_SEARCH)

    def save_indices(self):
        """Persiste los índices en disco (BM25 y FAISS)."""
        logger.info(f"Saving indices to {settings.INDEX_STORAGE_DIR}...")
        self.storage.save_lexical(self.lexical_index)
        self.storage.save_vector(self.semantic_index, doc_texts=self.semantic_doc_texts)
        logger.info("Saved successfully.")

    def load_indices(self) -> bool:
        """Carga índices desde disco; retorna True si encontró ambos archivos."""
        logger.info(f"Loading indices from {settings.INDEX_STORAGE_DIR}...")
        lex_ok = self.storage.load_lexical(self.lexical_index)
        vec_ok = self.storage.load_vector(self.semantic_index)
        
        if lex_ok and vec_ok:
            logger.info("Indices loaded successfully.")
            return True
        else:
            logger.warning("Could not find all index files.")
            return False
