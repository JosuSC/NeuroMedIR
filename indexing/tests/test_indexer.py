import os
import json
import logging
from indexing.indexer import Indexer
from indexing.configs import settings

logging.basicConfig(level=logging.INFO)

def load_processed_data() -> list:
    """Helper to load JSON files from the crawler."""
    docs = []
    if not settings.PROCESSED_DATA_DIR.exists():
        print(f"Directory {settings.PROCESSED_DATA_DIR} not found.")
        return docs
        
    for filename in os.listdir(settings.PROCESSED_DATA_DIR):
        if filename.endswith(".json"):
            filepath = settings.PROCESSED_DATA_DIR / filename
            with open(filepath, 'r', encoding='utf-8') as f:
                docs.append(json.load(f))
    return docs

def run_tests():
    print("=== NeuroMedIR Indexing Test ===")
    
    # 1. Load documents
    docs = load_processed_data()
    if not docs:
        print("No documents found to index. Did you run the crawler?")
        return
        
    # 2. Initialize Indexer
    indexer = Indexer()
    
    # 3. Index Documents
    indexer.index_documents(docs)
    
    # 4. Save
    indexer.save_indices()
    
    # 5. Load to verify state reconstitution
    new_indexer = Indexer()
    success = new_indexer.load_indices()
    if not success:
        print("Failed to load indices.")
        return

    # 6. Test Retrieval 
    # English Query
    en_query = "symptoms of heart attack"
    print(f"\n[EN] Lexical Search for: '{en_query}'")
    lex_res = new_indexer.search_lexical(en_query, top_k=3)
    print(lex_res)
    
    print(f"\n[EN] Semantic Search for: '{en_query}'")
    sem_res = new_indexer.search_semantic(en_query, top_k=3)
    print(sem_res)

    # Spanish Query
    es_query = "síntomas de un ataque al corazón"
    print(f"\n[ES] Lexical Search for: '{es_query}'")
    lex_res_es = new_indexer.search_lexical(es_query, top_k=3)
    print(lex_res_es)
    
    print(f"\n[ES] Semantic Search for: '{es_query}'")
    sem_res_es = new_indexer.search_semantic(es_query, top_k=3)
    print(sem_res_es)

if __name__ == "__main__":
    run_tests()
