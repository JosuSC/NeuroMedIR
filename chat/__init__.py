"""
chat — Módulo conversacional de NeuroMedIR.

Componentes:
    - IntentClassifier: Clasifica mensajes en saludo/pregunta/síntomas/despedida/no_médico
"""

from .intent_classifier import IntentClassifier, IntentType

__all__ = ["IntentClassifier", "IntentType"]