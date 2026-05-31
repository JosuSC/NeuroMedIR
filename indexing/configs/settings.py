import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "corpus_v2" / "processed"
INDEX_STORAGE_DIR = BASE_DIR / "indices"

os.makedirs(INDEX_STORAGE_DIR, exist_ok=True)

# Índices separados para documentos de expansión web dinámica
# El profesor indicó explícitamente que deben ser representaciones independientes
EXPANSION_DATA_DIR = DATA_DIR / "expansion" / "processed"
EXPANSION_INDEX_DIR = BASE_DIR / "indices_expansion"

os.makedirs(EXPANSION_DATA_DIR, exist_ok=True)
os.makedirs(EXPANSION_INDEX_DIR, exist_ok=True)

# Lexical configs
BM25_PARAMS = {
    "k1": 1.5,
    "b": 0.75
}

# Semantic configs
# "paraphrase-multilingual-MiniLM-L12-v2" is fast and robust for EN/ES semantic search
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384  # Dimensionality of the specific model above
EMBEDDING_BATCH_SIZE = 32

# Vector index (FAISS) configs
HNSW_M = 32
HNSW_EF_CONSTRUCTION = 120
HNSW_EF_SEARCH = 64
