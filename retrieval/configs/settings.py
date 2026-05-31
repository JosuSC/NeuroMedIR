# Retrieval module settings
# Fusion and ranking configuration for the hybrid retrieval pipeline.

# ---------------------------------------------------------------------------
# Fusion Strategy
# ---------------------------------------------------------------------------
# "rrf" = Reciprocal Rank Fusion (robust, parameter-light, state-of-the-art)
# "weighted" = Weighted linear combination of normalized scores
FUSION_STRATEGY = "rrf"

# RRF constant k (standard value from Cormack et al. 2009)
# Higher k → more weight on lower-ranked documents
RRF_K = 60

# Weights for weighted fusion (only used when FUSION_STRATEGY == "weighted")
# Must sum to 1.0 — higher semantic weight leverages the NN understanding
LEXICAL_WEIGHT = 0.3
SEMANTIC_WEIGHT = 0.7

# ---------------------------------------------------------------------------
# Retrieval Defaults
# ---------------------------------------------------------------------------
# How many candidates each sub-system retrieves before fusion
LEXICAL_TOP_K = 50
SEMANTIC_TOP_K = 50

# Final number of results returned to the user after fusion + re-ranking
FINAL_TOP_K = 10

# ---------------------------------------------------------------------------
# Neural Ranker (Stage 2 — Cross-Encoder Re-ranker)
# ---------------------------------------------------------------------------
# Cross-encoder model for re-ranking.
# This is the Stage 2 precision model that re-scores (query, doc) pairs.
# Set to None to disable cross-encoder re-ranking.
#
# Recommended models (from sentence-transformers):
#   - "cross-encoder/ms-marco-MiniLM-L-6-v2"  ← Fast, good quality (DEFAULT)
#   - "cross-encoder/ms-marco-MiniLM-L-12-v2"  ← Better quality, slower
#   - "cross-encoder/ms-marco-electra-base"     ← Best quality, much slower
#
# Reference: Nogueira & Cho (2019), Nogueira et al. (2020)
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Maximum number of candidates to re-rank with cross-encoder (cost control)
# These come from Stage 1 (RRF fusion) — more candidates = better recall but
# slower re-ranking. 20-50 is typical.
RERANK_TOP_K = 20

# Cross-encoder inference batch size
# Lower = less memory, higher = faster. 32 is safe for CPU; increase on GPU.
RERANK_BATCH_SIZE = 32

# Maximum sequence length for cross-encoder input (query + document tokens)
# 512 is the standard for MiniLM models. Documents are truncated to fit.
RERANK_MAX_LENGTH = 512


# ---------------------------------------------------------------------------
# Query Expansion
# ---------------------------------------------------------------------------
QUERY_EXPANSION_ENABLED = True

# Técnica 1: sinónimos estáticos
EXPANSION_USE_SYNONYMS = True

# Técnica 2: pseudo-relevance feedback
EXPANSION_USE_PRF = True

# Cuántos docs del retrieve inicial se analizan para PRF
PRF_TOP_DOCS = 3

# Cuántos términos TF-IDF se agregan a la query
PRF_TOP_TERMS = 5

# Score TF-IDF mínimo para que un término califique
PRF_MIN_SCORE = 0.1


# ---------------------------------------------------------------------------
# Multi-factor Ranker (Stage 3)
# ---------------------------------------------------------------------------
# Pesos del score compuesto — deben sumar 1.0
RANKER_W_RELEVANCE  = 0.60   # Score del cross-encoder
RANKER_W_SOURCE     = 0.20   # Confiabilidad de la fuente
RANKER_W_FRESHNESS  = 0.10   # Frescura del documento
RANKER_W_LANGUAGE   = 0.05   # Coincidencia de idioma con la query
RANKER_W_DIVERSITY  = 0.05   # Diversidad de fuentes

# Máximo de documentos del mismo dominio sin penalización
RANKER_MAX_PER_SOURCE = 2

# Peso por defecto para dominios no listados en SOURCE_RELIABILITY
RANKER_DEFAULT_SOURCE_WEIGHT = 0.60

# Vida media para el decay de frescura (en días)
# Un documento de esta antigüedad recibe score de frescura = 0.5
RANKER_FRESHNESS_HALF_LIFE_DAYS = 180