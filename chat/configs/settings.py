# chat/configs/settings.py — Configuración del módulo conversacional NeuroMedIR

# ---------------------------------------------------------------------------
# Clasificador de Intención
# ---------------------------------------------------------------------------
# Umbral reducido de 0.5 a 0.3 para que "hola mi amigo" clasifique como SALUDO
UMBRAL_SINTOMA = 0.35
UMBRAL_SALUDO = 0.3

# ---------------------------------------------------------------------------
# Motor de Diagnóstico
# ---------------------------------------------------------------------------
MAX_DIAGNOSTICOS = 8
MIN_PROBABILIDAD_DIAGNOSTICO = 1.0
DIAGNOSIS_TOP_K = 10

# ---------------------------------------------------------------------------
# Respuestas Conversacionales (fallback cuando no hay LLM disponible)
# ---------------------------------------------------------------------------
SALUDOS_ES = [
    "¡Hola! Soy NeuroMedIR, tu asistente de salud. Puedes preguntarme sobre síntomas, enfermedades, tratamientos o prevención. ¿En qué puedo ayudarte hoy?",
    "¡Bienvenido! Soy NeuroMedIR. Estoy aquí para responder tus consultas médicas. ¿Qué te gustaría saber?",
    "¡Hola! Me da gusto que estés aquí. Puedes preguntarme sobre cualquier tema de salud: síntomas, enfermedades, medicamentos o prevención.",
]

SALUDOS_EN = [
    "Hello! I'm NeuroMedIR, your health assistant. You can ask me about symptoms, diseases, treatments, or prevention. How can I help you today?",
    "Welcome! I'm NeuroMedIR. Feel free to ask me any medical question. What would you like to know?",
    "Hi there! I'm NeuroMedIR. Ask me about symptoms, diseases, medications, or any health topic you have in mind.",
]

DESPEDIDAS_ES = [
    "¡Cuídate! Recuerda que esta información no sustituye una consulta médica profesional. Si tienes dudas, consulta a tu doctor.",
    "¡Hasta luego! No olvides que siempre es importante consultar con un profesional de la salud para un diagnóstico definitivo.",
]

DESPEDIDAS_EN = [
    "Take care! Remember this information doesn't replace professional medical advice.",
    "Goodbye! Always remember to consult a healthcare professional for a definitive diagnosis.",
]

NO_MEDICO_ES = [
    "Soy un asistente especializado en temas de salud. Por favor, pregúntame sobre enfermedades, síntomas, tratamientos o prevención.",
    "Mi área de especialización es la salud médica. ¿Tienes alguna consulta sobre síntomas, enfermedades, o cómo prevenir alguna condición? Estoy aquí para ayudarte.",
]

NO_MEDICO_EN = [
    "I'm a health-specialized assistant. Please ask me about diseases, symptoms, treatments, or prevention.",
    "My area of expertise is medical health. Do you have any questions about symptoms, diseases, or how to prevent a condition? I'm here to help.",
]

# Disclaimer médico
DISCLAIMER_ES = (
    "⚠️ **Aviso importante:** Esta información es orientativa y no sustituye "
    "una consulta médica profesional. Consulte siempre a un profesional de la "
    "salud para un diagnóstico definitivo."
)

DISCLAIMER_EN = (
    "⚠️ **Important notice:** This information is guidance-only and does not "
    "replace professional medical advice. Always consult a healthcare "
    "professional for a definitive diagnosis."
)

# ---------------------------------------------------------------------------
# System Prompts para LLM (cuando está disponible)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_MEDICAL_ES = (
    "Eres NeuroMedIR, un asistente médico virtual profesional y empático. "
    "Te especializas en neurología y medicina general. "
    "Respondes SIEMPRE en español, con un tono profesional pero cálido, "
    "como lo haría un médico experimentado que se preocupa por su paciente. "
    "Explicas con detalle, usando lenguaje accesible pero preciso. "
    "Cuando menciones fuentes, usa [Fuente X]. "
    "NUNCA inventes información médica. Si no tienes información suficiente, dilo claramente. "
    "Siempre incluye un aviso de que tu información no sustituye una consulta profesional. "
    "Si el usuario pregunta sobre temas no médicos, redirígelo amablemente a consultas de salud."
)

SYSTEM_PROMPT_MEDICAL_EN = (
    "You are NeuroMedIR, a professional and empathetic virtual medical assistant. "
    "You specialize in neurology and general medicine. "
    "You ALWAYS respond in English, with a professional yet warm tone, "
    "like an experienced doctor who cares about their patient. "
    "You explain in detail, using accessible yet precise language. "
    "When citing sources, use [Source X]. "
    "NEVER invent medical information. If you lack sufficient information, say so clearly. "
    "Always include a disclaimer that your information does not replace professional consultation. "
    "If the user asks about non-medical topics, kindly redirect them to health-related queries."
)