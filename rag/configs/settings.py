# RAG module settings — NeuroMedIR
# All LLM inference runs locally. No external API required.

# ---------------------------------------------------------------------------
# LLM Generator Configuration
# ---------------------------------------------------------------------------
# Default model: google/flan-t5-base (220M params, CPU-friendly, instruction-tuned)
# Alternatives (better quality, need more RAM/GPU):
#   - "google/flan-t5-large"   (770M params, better quality, ~3GB RAM)
#   - "google/flan-t5-xl"      (3B params, excellent quality, ~10GB RAM)
#   - "mistralai/Mistral-7B-Instruct-v0.2" (7B, needs GPU or llama.cpp)
RAG_LLM_MODEL = "google/flan-t5-base"

# Device for inference: "cpu", "cuda", "auto"
# "auto" detects CUDA availability and falls back to CPU
RAG_LLM_DEVICE = "auto"

# ---------------------------------------------------------------------------
# Generation Parameters
# ---------------------------------------------------------------------------
RAG_TEMPERATURE = 0.3           # Low temperature → factual, deterministic responses
RAG_MAX_NEW_TOKENS = 512        # Maximum tokens the LLM generates per response
RAG_MIN_NEW_TOKENS = 50         # Minimum tokens to generate (avoids empty responses)
RAG_REPETITION_PENALTY = 1.2    # Penalize repetition (1.0 = no penalty)
RAG_NUM_BEAMS = 2               # Beam search width (1 = greedy, 2-4 = better quality)
RAG_TOP_P = 0.9                 # Nucleus sampling threshold
RAG_DO_SAMPLE = False           # False = beam search, True = sampling

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

# ---------------------------------------------------------------------------
# LLM Loading
# ---------------------------------------------------------------------------
RAG_LLM_LOAD_IN_8BIT = False    # 8-bit quantization (saves RAM, needs bitsandbytes)
RAG_LLM_LOW_CPU_MEM = True      # Reduce peak CPU memory during loading
