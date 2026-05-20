"""
llm_client.py — Local LLM Client for RAG Generation.

Uses HuggingFace Transformers for fully local inference.
No API keys, no cloud calls, no rate limits.

Architecture:
    BaseLLMClient (abstract) ← defines the interface
        └── TransformersLLMClient ← default implementation (flan-t5-base)

Design decisions:
    - Lazy loading: Model is NOT loaded at import time.
      Loads on first generate() call to avoid slowing startup.
    - Device auto-detection: Uses CUDA if available, CPU otherwise.
    - Token-aware: Tracks token usage for context window management.
    - Graceful degradation: Returns None on failure instead of crashing.

Algorithmic considerations:
    - Beam search (num_beams=2) by default for higher-quality outputs
      with O(beam_width * sequence_length) complexity.
    - Repetition penalty applied during decoding to avoid degenerate outputs.
    - Input truncation to max_length prevents OOM on long contexts.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

from .configs import settings as rag_settings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.

    Defines the interface that all LLM backends must implement.
    This allows swapping between Transformers, Ollama, llama.cpp, etc.
    without modifying the RAG pipeline.
    """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the LLM is loaded and ready for inference."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the name/identifier of the loaded model."""
        ...

    @abstractmethod
    def generate(self, prompt: str, max_new_tokens: int = None) -> Optional[str]:
        """
        Generates text from a prompt.

        Args:
            prompt: The input text prompt.
            max_new_tokens: Maximum tokens to generate (overrides config).

        Returns:
            Generated text string, or None if generation fails.
        """
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Counts the number of tokens in a text string.

        Used for context window management and truncation decisions.
        Returns an estimate if exact tokenization is unavailable.
        """
        ...


class TransformersLLMClient(BaseLLMClient):
    """
    Local LLM client using HuggingFace Transformers.

    Loads a seq2seq model (e.g., flan-t5-base) and runs inference
    entirely on the local machine. No API keys required.

    Complexity:
        - Loading: O(model_size) — one-time cost
        - Generation: O(num_beams * max_new_tokens * vocab_size) per call
        - Tokenization: O(n) where n = text length

    Memory: ~1GB for flan-t5-base on CPU, ~3GB for flan-t5-large.

    Usage:
        client = TransformersLLMClient()
        if client.is_available:
            response = client.generate("What is diabetes?")
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        load_in_8bit: bool = False,
        low_cpu_mem_usage: bool = True,
    ):
        """
        Args:
            model_name: HuggingFace model identifier.
                        Defaults to settings.RAG_LLM_MODEL.
            device: Device string ("cpu", "cuda", "auto").
                    "auto" = CUDA if available, else CPU.
            load_in_8bit: Use 8-bit quantization (needs bitsandbytes).
            low_cpu_mem_usage: Reduce peak CPU memory during model loading.
        """
        self._model_name = model_name or rag_settings.RAG_LLM_MODEL
        self._device = self._resolve_device(device)
        self._load_in_8bit = load_in_8bit
        self._low_cpu_mem_usage = low_cpu_mem_usage

        # Lazy-loaded: None until first generate() call
        self._model = None
        self._tokenizer = None
        self._generator = None
        self._loaded = False

        logger.info(
            f"TransformersLLMClient: Will load '{self._model_name}' "
            f"on device '{self._device}' on first use (lazy loading)."
        )

    @staticmethod
    def _resolve_device(device: Optional[str]) -> str:
        """Resolves the device string, handling 'auto' detection."""
        if device is None or device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device

    # -------------------------------------------------------------------
    # Lazy loading
    # -------------------------------------------------------------------

    def _load(self) -> bool:
        """
        Loads the model and tokenizer into memory (lazy, called once).

        Uses a HuggingFace pipeline for clean abstraction over
        tokenization + generation + decoding.

        Returns:
            True if loaded successfully, False otherwise.
        """
        if self._loaded:
            return self._model is not None

        try:
            logger.info(f"Loading LLM model: {self._model_name}...")

            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_name,
                legacy=False,
            )

            # Load model
            model_kwargs = {
                "low_cpu_mem_usage": self._low_cpu_mem_usage,
            }
            if self._load_in_8bit and self._device == "cuda":
                model_kwargs["load_in_8bit"] = True
            else:
                model_kwargs["torch_dtype"] = torch.float32

            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                self._model_name,
                **model_kwargs,
            )
            self._model.to(self._device)
            self._model.eval()  # Set to inference mode

            # Create pipeline for clean generation
            self._generator = pipeline(
                "text2text-generation",
                model=self._model,
                tokenizer=self._tokenizer,
                device=0 if self._device == "cuda" else -1,
            )

            self._loaded = True
            param_count = sum(p.numel() for p in self._model.parameters()) / 1e6
            logger.info(
                f"LLM loaded successfully: {self._model_name} "
                f"({param_count:.1f}M params, device: {self._device})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to load LLM model '{self._model_name}': {e}. "
                f"RAG generation will be unavailable."
            )
            self._loaded = True  # Don't retry on every call
            self._model = None
            return False

    # -------------------------------------------------------------------
    # Public API (implements BaseLLMClient)
    # -------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Returns True if the LLM is ready for inference."""
        if not self._loaded:
            return True  # Not loaded yet but should be loadable
        return self._model is not None

    @property
    def model_name(self) -> str:
        """Returns the configured model name."""
        return self._model_name

    def generate(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        Generates text from a prompt using the local model.

        Uses beam search by default for higher-quality outputs.
        Applies repetition penalty to avoid degenerate text.

        Args:
            prompt: The input text prompt.
            max_new_tokens: Override for max generation tokens.

        Returns:
            Generated text string, or None if generation fails.
        """
        # Lazy load
        if not self._loaded:
            self._load()

        if self._generator is None:
            logger.warning("LLM: Model not available — cannot generate.")
            return None

        if not prompt or not prompt.strip():
            logger.warning("LLM: Empty prompt — skipping generation.")
            return None

        max_tokens = max_new_tokens or rag_settings.RAG_MAX_NEW_TOKENS

        try:
            # Truncate input if it exceeds the model's max length
            max_input_length = getattr(
                self._tokenizer, "model_max_length", 512
            )
            inputs = self._tokenizer(
                prompt,
                truncation=True,
                max_length=max_input_length - max_tokens,
                return_tensors="pt",
            ).to(self._device)

            # Generate with beam search
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    min_new_tokens=rag_settings.RAG_MIN_NEW_TOKENS,
                    num_beams=rag_settings.RAG_NUM_BEAMS,
                    repetition_penalty=rag_settings.RAG_REPETITION_PENALTY,
                    temperature=rag_settings.RAG_TEMPERATURE if rag_settings.RAG_DO_SAMPLE else 1.0,
                    top_p=rag_settings.RAG_TOP_P if rag_settings.RAG_DO_SAMPLE else 1.0,
                    do_sample=rag_settings.RAG_DO_SAMPLE,
                    early_stopping=True,
                )

            # Decode output (skip special tokens)
            generated_text = self._tokenizer.decode(
                outputs[0],
                skip_special_tokens=True,
            ).strip()

            if not generated_text:
                logger.warning("LLM: Generated empty text.")
                return None

            logger.info(
                f"LLM: Generated {len(generated_text)} chars "
                f"from {inputs['input_ids'].shape[1]} input tokens"
            )
            return generated_text

        except Exception as e:
            logger.error(f"LLM: Generation failed: {e}")
            return None

    def count_tokens(self, text: str) -> int:
        """
        Counts tokens using the loaded tokenizer.

        Falls back to character-based estimation if tokenizer is unavailable.
        """
        if self._tokenizer is not None:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                pass

        # Fallback: heuristic estimation
        return len(text) // rag_settings.RAG_CHARS_PER_TOKEN

    def __repr__(self) -> str:
        status = "loaded" if self._model is not None else "pending"
        return (
            f"TransformersLLMClient(model='{self._model_name}', "
            f"device='{self._device}', status={status})"
        )

