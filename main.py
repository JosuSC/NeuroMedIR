import logging
import time
import sys

# Corrige Unicode issues en consola Windows
sys.stdout.reconfigure(encoding="utf-8")

from dynamic_expansion import expand_corpus_from_query

# Modulos para cargar el buscador
from retrieval.retriever import Retriever
from indexing.indexer import Indexer
from indexing.lexical_index.bm25_index import BM25Index
from indexing.vector_index.faiss_hnsw import FAISSHNSWIndex
from indexing.multimodal.text_encoder import TextEncoder
from retrieval.document_store import DocumentStore
from indexing.storage.index_io import IndexStorage
from indexing.configs import settings as idx_settings

logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

def get_loaded_indexer(bm25, faiss, encoder, io):
    indexer = Indexer()
    indexer.lexical_index = bm25
    indexer.semantic_index = faiss
    indexer.encoder = encoder
    indexer.storage = io
    return indexer

def main():
    print("=" * 60)
    print("=== NeuroMedIR: Sistema Híbrido de Búsqueda Médica ===")
    print("=" * 60)
    
    print("Inicializando Motor BM25 + FAISS...")
    bm25 = BM25Index(k1=idx_settings.BM25_PARAMS["k1"], b=idx_settings.BM25_PARAMS["b"])
    faiss = FAISSHNSWIndex(dimension=idx_settings.EMBEDDING_DIM, m=idx_settings.HNSW_M, ef_construction=idx_settings.HNSW_EF_CONSTRUCTION)
    encoder = TextEncoder(idx_settings.EMBEDDING_MODEL_NAME)
    doc_store = DocumentStore(idx_settings.PROCESSED_DATA_DIR)
    io = IndexStorage(str(idx_settings.INDEX_STORAGE_DIR))

    success = io.load_lexical(bm25) and io.load_vector(faiss)
    if not success:
        print("⚠️ No se pudieron cargar los índices de disco. Ejecuta `python run_indexing.py` primero.")
        return

    retriever = Retriever(bm25, faiss, encoder, doc_store)
    indexer = get_loaded_indexer(bm25, faiss, encoder, io)
    
    print(f"✔ Índices cargados: {doc_store.count} documentos en memoria local.")

    while True:
        query = input("\nIngrese su consulta médica (o 'salir' para terminar): ").strip()
        if query.lower() in ["salir", "exit", "quit", "q"]:
            break
            
        if not query:
            continue

        print(f"\n>> Buscando '{query}' en base de datos local (BM25 + FAISS)...")
        # 2. Búsqueda Híbrida local
        t_start = time.time()
        results = retriever.retrieve(query, top_k=5)
        
        if results:
            for i, res in enumerate(results, 1):
                title = res.get("title", "Sin título")
                score = res.get("score", 0.0)
                url = res.get("url", "")
                print(f"[{i}] {title[:80]}... | Score Híbrido: {score:.4f} \n    ⮑ {url}")
            print(f"Tiempo de búsqueda local: {(time.time() - t_start)*1000:.1f}ms")
        else:
            print("No se encontró información relevante en el corpus actual local.")
        
        # 3. Llamar a la expansión dinámica para inyectar nuevos documentos
        print(f"\n>> Consultando la web en tiempo real para expandir sobre '{query}'...")
        nuevos_documentos = expand_corpus_from_query(query, max_new_docs=3)
        
        if nuevos_documentos:
            print(f"\n¡Éxito! El sistema ha extraído {len(nuevos_documentos)} documentos nuevos.")
            for i, doc in enumerate(nuevos_documentos, 1):
                titulo = doc.get("title", "Sin título")
                url = doc.get("url", "")
                print(f" [+] Nuevos conocimientos: {titulo[:80]}... \n     [URL: {url}]")
            
            # 4. Actualizar los índices dinámicamente
            print("\nIntegrando la nueva información a los modelos vectoriales y BM25...")
            indexer.add_documents(nuevos_documentos)
            
            # 5. Forzar actualización del Storage en memoria
            doc_store._load() 
            print(f"Corpus y Modelos actualizados: {doc_store.count} documentos en base de datos.")
        else:
            print("\nNo se encontraron artículos nuevos rápidos en esta expansión.")

if __name__ == "__main__":
    main()
