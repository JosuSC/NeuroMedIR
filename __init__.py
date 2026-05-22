"""
NeuroMedIR — Sistema Híbrido de Recuperación de Información Médica.

Módulos principales:
    - scraper:    Extracción de contenido web (fetch, parse, extract)
    - crawler:    Crawling BFS para construcción de corpus
    - indexing:   Indexación BM25 + FAISS
    - retrieval:  Recuperación híbrida con re-ranking neuronal
    - rag:        Generación aumentada por recuperación (LLM local)
    - form:       Generación dinámica de formularios PRF
"""
