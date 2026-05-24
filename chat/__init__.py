"""
chat — Módulo de conversación inteligente para NeuroMedIR.

Arquitectura del flujo conversacional:
    Mensaje del usuario
        ↓
    Clasificador de Intención (IntentClassifier)
        ↓
    ┌──────────────────────────────────────────────┐
    │ SALUDO → Respuesta amigable conversacional   │
    │ PREGUNTA → RAG → Respuesta + Bibliografía    │
    │ SÍNTOMAS → Formulario dinámico → Diagnóstico │
    └──────────────────────────────────────────────┘

Este módulo reemplaza el flujo anterior donde TODO se trataba
como una consulta médica de retrieval directo.
"""

from .intent_classifier import IntentClassifier
from .diagnosis_engine import DiagnosisEngine

__all__ = ["IntentClassifier", "DiagnosisEngine"]
