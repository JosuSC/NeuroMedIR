"""
chat — Módulo conversacional de NeuroMedIR.

Componentes:
    - IntentClassifier: Clasifica mensajes en saludo/pregunta/síntomas/despedida/no_médico
    - DiagnosisEngine: Genera diagnósticos diferenciales (LLM-driven con fallback)
"""

from .intent_classifier import IntentClassifier, IntentType
from .diagnosis_engine import DiagnosisEngine

__all__ = ["IntentClassifier", "IntentType", "DiagnosisEngine"]