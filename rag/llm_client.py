"""Gemini-backed LLM client for RAG generation."""

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

import requests
from dotenv import load_dotenv

from .configs import settings as rag_settings

load_dotenv()

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


class GeminiLLMClient(BaseLLMClient):
    """Gemini client that calls Google's Generative Language API."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ):
        """
        Args:
            model_name: Gemini model identifier.
            api_key: Gemini API key. Falls back to environment variables.
            temperature: Sampling temperature.
            top_p: Nucleus sampling value.
            top_k: Top-K sampling value.
            timeout_seconds: HTTP timeout for each request.
        """
        self._model_name = model_name or rag_settings.RAG_LLM_MODEL
        self._api_key = (
            api_key
            or os.getenv(rag_settings.GEMINI_API_KEY_ENV)
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self._temperature = temperature if temperature is not None else rag_settings.GEMINI_TEMPERATURE
        self._top_p = top_p if top_p is not None else rag_settings.GEMINI_TOP_P
        self._top_k = top_k if top_k is not None else rag_settings.GEMINI_TOP_K
        self._timeout_seconds = timeout_seconds or rag_settings.GEMINI_REQUEST_TIMEOUT_SECONDS
        self._endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model_name}:generateContent"
        )

        if self._api_key:
            logger.info("GeminiLLMClient: using model '%s'.", self._model_name)
        else:
            logger.warning(
                "GeminiLLMClient: no API key found. Set %s in the environment or .env.",
                rag_settings.GEMINI_API_KEY_ENV,
            )

    # -------------------------------------------------------------------
    # Public API (implements BaseLLMClient)
    # -------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Returns True if the Gemini client has credentials configured."""
        return bool(self._api_key)

    @property
    def model_name(self) -> str:
        """Returns the configured Gemini model name."""
        return self._model_name

    def generate(
        self,
        prompt: str,
        max_new_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Generates text using the Gemini API."""
        if not self._api_key:
            logger.warning("LLM: Gemini API key not configured — cannot generate.")
            return None

        if not prompt or not prompt.strip():
            logger.warning("LLM: Empty prompt — skipping generation.")
            return None

        max_tokens = max_new_tokens or rag_settings.RAG_MAX_NEW_TOKENS

        try:
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": {
                    "temperature": self._temperature,
                    "topP": self._top_p,
                    "topK": self._top_k,
                    "maxOutputTokens": max_tokens,
                },
            }

            response = requests.post(
                self._endpoint,
                params={"key": self._api_key},
                json=payload,
                timeout=self._timeout_seconds,
            )

            if not response.ok:
                logger.error(
                    "Gemini request failed (%s): %s",
                    response.status_code,
                    response.text[:1000],
                )
                return None

            data = response.json()
            generated_text = self._extract_text(data)
            if not generated_text:
                logger.warning("Gemini: empty response payload.")
                return None

            return generated_text.strip()

        except Exception as e:
            logger.error("LLM: Generation failed: %s", e)
            return None

    def count_tokens(self, text: str) -> int:
        """Returns a rough token estimate for Gemini prompts."""
        if not text:
            return 0
        return max(1, len(text) // rag_settings.RAG_CHARS_PER_TOKEN)

    @staticmethod
    def _extract_text(payload: dict) -> Optional[str]:
        candidates = payload.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
            combined = "".join(texts).strip()
            if combined:
                return combined

        alt = payload.get("output_text")
        if isinstance(alt, str) and alt.strip():
            return alt.strip()
        return None

    def __repr__(self) -> str:
        status = "configured" if self._api_key else "missing_key"
        return f"GeminiLLMClient(model='{self._model_name}', status={status})"


TransformersLLMClient = GeminiLLMClient

