"""
rag — Retrieval-Augmented Generation module for NeuroMedIR.

Architecture:
    Retriever (BM25+FAISS+CrossEncoder) → Context Builder → Gemini LLM → Response Parser
"""

from .pipeline import RAGPipeline
from .llm_client import BaseLLMClient, GeminiLLMClient, TransformersLLMClient

__all__ = ["RAGPipeline", "BaseLLMClient", "GeminiLLMClient", "TransformersLLMClient"]