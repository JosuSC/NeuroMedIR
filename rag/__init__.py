"""
rag — Retrieval-Augmented Generation module for NeuroMedIR.

Architecture:
    Retriever (BM25+FAISS+CrossEncoder) → Context Builder → Local LLM → Response Parser

The LLM generator runs entirely locally using HuggingFace Transformers.
No external API calls or cloud services are required.
"""

from .pipeline import RAGPipeline
from .llm_client import BaseLLMClient, TransformersLLMClient

__all__ = ["RAGPipeline", "BaseLLMClient", "TransformersLLMClient"]