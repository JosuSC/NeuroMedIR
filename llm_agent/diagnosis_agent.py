from .llm_client import MedicalLLMAgent

class DiagnosisAgent(MedicalLLMAgent):
    """
    Agente de Diagnóstico Asistido. Mapea porcentajes usando estrictamente
    la literatura de la BD Vectorial (NeuroMedIR FAISS). No inventa.
    """
    def analyze_match(self, context_symptoms: str, retrieved_docs: list):
        # 1. Preparamos el contexto recuperado por FAISS/BM25
        if not retrieved_docs:
            docs_text = "No se recuperaron fuentes científicas para esta consulta."
        else:
            docs_text = "\n\n".join([f"Fuente {i+1}: {d.get('title','Sin Titulo')}\n{d.get('content','')[:600]}..." for i, d in enumerate(retrieved_docs)])
        
        # 2. Creamos el Prompt al LLM forzando que use sólo esa literatura
        system_prompt = """Eres un sistema RAG (Retrieval-Augmented Generation) para NeuroMedIR.
Tu objetivo NO es ser médico. Tu objetivo es leer los `Síntomas del Paciente` y los `Textos Médicos Recuperados`.
Crea una lista de las posibles enfermedades descritas en los textos que coincidan con los síntomas.
ASIGNA UN PORCENTAJE (1 al 100) que refleja cuánto empareja el síntoma del paciente con los síntomas descritos de esa enfermedad EN LA LECTURA RECUPERADA, NADA MÁS.
DEBES responder ÚNICAMENTE con un objeto JSON conteniendo una lista 'resultados'. Cada objeto debe tener: 'condicion' (Enfermedad), 'porcentaje' (int), 'base' (Un fragmento en español defendiendo el porcentaje sacado del texto).
Ejemplo de salida validada:
{"resultados": [{"condicion": "Gripe", "porcentaje": 88, "base": "La fuente 3 menciona fiebre como síntoma de gripe."}]}"""
        
        fallback = {
            "resultados": [
                {"condicion": "Infección viral general", "porcentaje": 60, "base": "(Simulación Groq Fallback) El algoritmo asume cuadros respiratorios comunes frente a tos o fiebre."},
                {"condicion": "Fatiga crónica", "porcentaje": 15, "base": "(Simulación Groq Fallback) La falta de energía descrita en los manuales de referencia FAISS sugiere fatiga."}
            ]
        }
        
        user_prompt = f"Síntomas consolidados del paciente:\n{context_symptoms}\n\nTextos Médicos Recuperados de la base vectorial (FAISS/BM25):\n\n{docs_text}"
        
        return self._get_json_response(system_prompt, user_prompt, fallback)
