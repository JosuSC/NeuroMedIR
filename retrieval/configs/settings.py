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

# Final number of results returned to the user after fusion
FINAL_TOP_K = 10

# ---------------------------------------------------------------------------
# Neural Ranker
# ---------------------------------------------------------------------------
# Cross-encoder model for re-ranking (optional, high-quality but slower)
# Set to None to disable cross-encoder re-ranking
CROSS_ENCODER_MODEL = None  # e.g. "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Maximum number of candidates to re-rank with cross-encoder (cost control)
RERANK_TOP_K = 20
