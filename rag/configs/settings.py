# RAG module settings — NeuroMedIR
# RAG generation uses Google Gemini via API key.

# ---------------------------------------------------------------------------
# LLM Generator Configuration
# ---------------------------------------------------------------------------
# Default model: Gemini Flash for fast, low-cost generation.
RAG_LLM_MODEL = "gemini-2.5-flash"

# API key environment variable used by the Gemini client.
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"

# OpenRouter API key environment variable.
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"

# OpenRouter API defaults (OpenAI-compatible endpoint).
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
OPENROUTER_REQUEST_TIMEOUT_SECONDS = 90

# Gemini request timeout.
GEMINI_REQUEST_TIMEOUT_SECONDS = 90

# Gemini generation defaults.
GEMINI_TEMPERATURE = 0.3
GEMINI_TOP_P = 0.9
GEMINI_TOP_K = 40

# OpenRouter generation defaults.
OPENROUTER_TEMPERATURE = 0.3
OPENROUTER_TOP_P = 0.9

# ---------------------------------------------------------------------------
# Generation Parameters
# ---------------------------------------------------------------------------
RAG_TEMPERATURE = GEMINI_TEMPERATURE
RAG_MAX_NEW_TOKENS = 2048       # Maximum tokens the LLM generates per response
RAG_MIN_NEW_TOKENS = 50         # Minimum tokens to generate (avoids empty responses)
RAG_CONTINUATION_MAX_TOKENS = 256  # Tokens for finishing incomplete answers
RAG_CONTINUATION_MAX_ATTEMPTS = 3  # Extra calls to finish a cut-off response
RAG_REPETITION_PENALTY = 1.2    # Kept for compatibility with older configs
RAG_NUM_BEAMS = 2               # Kept for compatibility with older configs
RAG_TOP_P = GEMINI_TOP_P
RAG_DO_SAMPLE = False           # Kept for compatibility with older configs

# ---------------------------------------------------------------------------
# Context Window
# ---------------------------------------------------------------------------
RAG_MAX_CONTEXT_TOKENS = 2048   # Max tokens for context (input documents)
RAG_CHARS_PER_TOKEN = 4         # Heuristic: avg 4 chars per token for English/Spanish

# ---------------------------------------------------------------------------
# Retrieval Parameters (RAG-specific, override retrieval defaults)
# ---------------------------------------------------------------------------
RAG_TOP_K = 5                   # Number of documents to retrieve per query
RAG_MIN_SCORE_THRESHOLD = 0.1   # Minimum retrieval score to include a document

