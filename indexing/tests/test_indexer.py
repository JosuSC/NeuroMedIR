import json
import logging
from indexing.indexer import Indexer
from indexing.configs import settings

logging.basicConfig(level=logging.INFO)

def load_processed_data() -> list:
    """Helper to load processed JSON files recursively from category folders."""
    docs = []
    if not settings.PROCESSED_DATA_DIR.exists():
        print(f"Directory {settings.PROCESSED_DATA_DIR} not found.")
        return docs

    for filepath in settings.PROCESSED_DATA_DIR.rglob("*.json"):
        if filepath.is_file():
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
    assert len(docs) > 0, "Expected at least one processed document"
    for doc in docs:
        assert isinstance(doc, dict), "Each loaded document must be a dictionary"
        assert "id" in doc and "title" in doc and "content" in doc, (
            "Each document must include id/title/content"
        )
        
    # 2. Initialize Indexer
    indexer = Indexer()
    
    # 3. Index Documents
    indexer.index_documents(docs)
    assert indexer.lexical_index.bm25 is not None, "BM25 index was not built"
    assert indexer.semantic_index.index is not None, "FAISS index was not built"
    assert len(indexer.lexical_index.doc_ids) > 0, "No doc_ids were indexed"
    
    # 4. Save
    indexer.save_indices()
    
    # 5. Load to verify state reconstitution
    new_indexer = Indexer()
    success = new_indexer.load_indices()
    if not success:
        print("Failed to load indices.")
        return
    assert success is True, "Indices should load successfully"

    # 6. Test Retrieval 
    # English Query
    en_query = "symptoms of heart attack"
    print(f"\n[EN] Lexical Search for: '{en_query}'")
    lex_res = new_indexer.search_lexical(en_query, top_k=3)
    print(lex_res)
    assert isinstance(lex_res, list), "Lexical search must return a list"
    if lex_res:
        assert "doc_id" in lex_res[0] and "score" in lex_res[0], "Invalid lexical result schema"
    
    print(f"\n[EN] Semantic Search for: '{en_query}'")
    sem_res = new_indexer.search_semantic(en_query, top_k=3)
    print(sem_res)
    assert isinstance(sem_res, list), "Semantic search must return a list"
    if sem_res:
        assert "doc_id" in sem_res[0], "Semantic result must include doc_id"

    # Spanish Query
    es_query = "síntomas de un ataque al corazón"
    print(f"\n[ES] Lexical Search for: '{es_query}'")
    lex_res_es = new_indexer.search_lexical(es_query, top_k=3)
    print(lex_res_es)
    assert isinstance(lex_res_es, list), "Spanish lexical search must return a list"
    
    print(f"\n[ES] Semantic Search for: '{es_query}'")
    sem_res_es = new_indexer.search_semantic(es_query, top_k=3)
    print(sem_res_es)
    assert isinstance(sem_res_es, list), "Spanish semantic search must return a list"

    print("\nAll indexing checks passed.")

if __name__ == "__main__":
    run_tests()
