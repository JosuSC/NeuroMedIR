# chat/configs/settings.py — Configuración del módulo conversacional NeuroMedIR
# ---------------------------------------------------------------------------
# Parámetros para el clasificador de intención, motor de diagnóstico
# y respuestas conversacionales.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Clasificador de Intención
# ---------------------------------------------------------------------------
# Umbral de confianza para clasificar como SÍNTOMA.
# Si el score de síntomas >= UMBRAL_SINTOMA, se genera formulario.
# Rango: 0.0 - 1.0. Más bajo = más sensible a síntomas.
UMBRAL_SINTOMA = 0.35

# Umbral para clasificar como SALUDO.
# Si el score de saludo >= UMBRAL_SALUDO, se responde conversacionalmente.
UMBRAL_SALUDO = 0.5

# ---------------------------------------------------------------------------
# Motor de Diagnóstico
# ---------------------------------------------------------------------------
# Número máximo de diagnósticos diferenciales a mostrar al paciente.
MAX_DIAGNOSTICOS = 8

# Score mínimo (0-100%) para incluir un diagnóstico en la lista.
# Diagnósticos con probabilidad menor se descartan.
MIN_PROBABILIDAD_DIAGNOSTICO = 1.0

# Número de documentos a recuperar para generar diagnósticos.
DIAGNOSIS_TOP_K = 10

# ---------------------------------------------------------------------------
# Respuestas Conversacionales
# ---------------------------------------------------------------------------
# Respuestas predefinidas para saludos y despedidas.
SALUDOS_ES = [
    "¡Hola! Soy NeuroMedIR, tu asistente médico. ¿En qué puedo ayudarte hoy? Puedes contarme tus síntomas o hacerme preguntas sobre condiciones médicas.",
    "¡Bienvenido! Soy NeuroMedIR. Estoy aquí para ayudarte con consultas médicas. ¿Qué te preocupa hoy?",
    "¡Hola! Me da gusto que estés aquí. Soy NeuroMedIR, tu asistente de salud. Puedes preguntarme sobre síntomas, enfermedades o cualquier tema médico.",
]

SALUDOS_EN = [
    "Hello! I'm NeuroMedIR, your medical assistant. How can I help you today? You can tell me your symptoms or ask questions about medical conditions.",
    "Welcome! I'm NeuroMedIR. I'm here to help with medical queries. What's on your mind today?",
    "Hi there! Great to have you here. I'm NeuroMedIR, your health assistant. You can ask me about symptoms, diseases, or any medical topic.",
]

DESPEDIDAS_ES = [
    "¡Cuídate! Recuerda que esta información no sustituye una consulta médica profesional. Si tienes dudas, consulta a tu doctor.",
    "¡Hasta luego! No olvides que siempre es importante consultar con un profesional de la salud para un diagnóstico definitivo.",
]

DESPEDIDAS_EN = [
    "Take care! Remember this information doesn't replace professional medical advice. If in doubt, consult your doctor.",
    "Goodbye! Always remember to consult a healthcare professional for a definitive diagnosis.",
]

# Mensaje de disclaimer médico que se agrega a respuestas de diagnóstico
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
