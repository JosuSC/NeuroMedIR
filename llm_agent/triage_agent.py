from .llm_client import MedicalLLMAgent

class TriageAgent(MedicalLLMAgent):
    """
    Agente Entrevistador. Genera preguntas para el paciente basándose
    en la queja inicial o síntomas confusos.
    """
    def generate_questions(self, initial_symptoms: str):
        system_prompt = """Eres un asistente de pre-diagnóstico médico que guía a pacientes.
Tu objetivo es analizar el síntoma inicial y generar EXACTAMENTE 3 preguntas de opción múltiple para precisar el cuadro clínico (Ej: duración, tipo de dolor, acompañamiento sistémico).
NO DES DIAGNÓSTICOS, SOLO PREGUNTA.
DEBES responder ÚNICAMENTE con un objeto JSON con la clave 'preguntas', que contenga una lista de objetos, cada uno con 'pregunta' (str) y 'opciones' (array de strings).
Ejemplo de salida válida y requerida:
{"preguntas": [{"pregunta": "¿Hace cuánto tiene dolor?", "opciones": ["Hoy", "Hace una semana"]}, {"pregunta": "¿Tiene fiebre?", "opciones": ["Sí", "No"]}]}"""
        
        fallback = {
            "preguntas": [
                {"pregunta": "¿Hace cuánto empezaron los síntomas?", "opciones": ["Hoy", "Ayer", "Hace más de 3 días"]},
                {"pregunta": "¿El dolor o molestia es constante o intermitente?", "opciones": ["Constante", "Intermitente"]},
                {"pregunta": "¿Viene acompañado de otros síntomas como fiebre o debilidad?", "opciones": ["Fiebre", "Debilidad", "Ambos", "Ninguno"]}
            ]
        }
        
        user_prompt = f"El paciente reporta los siguientes síntomas u origen: '{initial_symptoms}'. Genera las preguntas aclaratorias."
        
        return self._get_json_response(system_prompt, user_prompt, fallback)
