import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class MedicalLLMAgent:
    """Clase base para todos los agentes LLM de NeuroMedIR usando Groq (gratis y rápido)"""
    
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        # Modelo recomendado = rápido, razonamiento clínico decente
        self.model = "llama-3.1-8b-instant" 
        
    def _get_json_response(self, system_prompt: str, user_prompt: str, fallback_response: dict):
        if not self.client:
            print("Advertencia: No se encontró GROQ_API_KEY. Usando fallback simulado para testing.")
            return fallback_response
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=0.1 # Muy baja temperatura para que no invente sino que extraiga
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Error en LLM Groq: {e}")
            return fallback_response
