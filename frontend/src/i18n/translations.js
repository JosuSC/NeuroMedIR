import React from 'react';

export const translations = {
    es: {
        // --- Estado del sistema ---
        systemConnected: 'Sistema Conectado',
        newMedicalSession: 'NUEVA SESIÓN MÉDICA',
        connectingEngines: 'Conectando motores neuronales...',

        // --- Chat ---
        enterMedicalQuery: 'Escriba su consulta médica o cuénteme sus síntomas...',
        processingResponse: 'Analizando su consulta...',
        searchingWeb: 'Buscando en internet si es necesario...',
        connectionError: 'Error de conexión',
        ensureDatabase: 'Asegúrese de que el servidor NeuroMedIR esté corriendo.',

        // --- Bienvenida ---
        welcome: '¡Hola! Soy NeuroMedIR, tu asistente médico inteligente.\n\nPuedes preguntarme sobre cualquier tema de salud o contarme tus síntomas y te ayudaré a entenderlos mejor. Si me cuentas qué sientes, generaré un formulario personalizado para darte un análisis más preciso.',

        // --- Formulario de síntomas ---
        fillForm: 'Complete el formulario',
        submitForm: 'Enviar formulario',
        intensity: 'Intensidad',
        duration: 'Duración',
        additionalNotes: 'Notas adicionales',
        detectedSymptoms: 'Síntomas detectados',
        dynamicSymptoms: 'Síntomas relacionados',
        selectDuration: 'Seleccione la duración',
        placeholderNotes: 'Ej. Soy diabético, tomo Losartán...',

        // --- Diagnóstico ---
        possibleDiagnoses: 'Posibles condiciones',
        probability: 'Probabilidad',
        bibliography: 'Bibliografía',
        sources: 'Fuentes consultadas',
        supportedBy: 'Sustentado por',

        // --- Respuestas ---
        greeting: 'saludo',
        question: 'pregunta',
        symptoms: 'síntomas',
        farewell: 'despedida',
        diagnosis: 'diagnóstico',

        // --- Controles ---
        uploadNeuroimage: 'Subir Neuroimagen (MRI/CT)',
        visualSearch: 'Búsqueda Visual',
        readMore: 'Leer más',
        noSnippet: 'Sin fragmento disponible',
        expandingSearch: 'Ampliando búsqueda en la web...',
        recoveredSources: 'Fuentes Recuperadas',
        primarySources: 'Fuentes primarias',
        backgroundSources: 'Contexto y guias',
        otherSources: 'Otras fuentes',
        sourceLabel: 'Fuente',
        typeLabel: 'Tipo',
        researchArticle: 'Articulo cientifico',
        healthTopic: 'Tema de salud',
        otherType: 'Otro',

        // --- Tema ---
        switchToLight: 'Cambiar a modo claro',
        switchToDark: 'Cambiar a modo oscuro',
        language: 'Idioma',

        // --- Evaluación ---
        assessmentProgress: 'Progreso de Evaluación',
        complete: 'Completar',
        cerebrovascularAssessment: 'Evaluación Cerebrovascular',
        basedOnDizziness: 'Basado en el mareo reportado, proporcione detalles específicos.',
        consult: 'Consultar',
        assessment: 'Evaluación',
        previous: 'Anterior',
        continue: 'Continuar a Análisis',
    },
    en: {
        // --- System status ---
        systemConnected: 'System Connected',
        newMedicalSession: 'NEW MEDICAL SESSION',
        connectingEngines: 'Connecting neural engines...',

        // --- Chat ---
        enterMedicalQuery: 'Write your medical query or tell me your symptoms...',
        processingResponse: 'Analyzing your query...',
        searchingWeb: 'Searching the web if needed...',
        connectionError: 'Connection error',
        ensureDatabase: 'Make sure the NeuroMedIR server is running.',

        // --- Welcome ---
        welcome: 'Hello! I\'m NeuroMedIR, your intelligent medical assistant.\n\nYou can ask me about any health topic or tell me your symptoms and I\'ll help you understand them better. If you tell me what you\'re feeling, I\'ll generate a personalized form for a more precise analysis.',

        // --- Symptom form ---
        fillForm: 'Fill out the form',
        submitForm: 'Submit form',
        intensity: 'Intensity',
        duration: 'Duration',
        additionalNotes: 'Additional notes',
        detectedSymptoms: 'Detected symptoms',
        dynamicSymptoms: 'Related symptoms',
        selectDuration: 'Select duration',
        placeholderNotes: 'E.g. I\'m diabetic, taking Losartan...',

        // --- Diagnosis ---
        possibleDiagnoses: 'Possible conditions',
        probability: 'Probability',
        bibliography: 'Bibliography',
        sources: 'Consulted sources',
        supportedBy: 'Supported by',

        // --- Response types ---
        greeting: 'greeting',
        question: 'question',
        symptoms: 'symptoms',
        farewell: 'farewell',
        diagnosis: 'diagnosis',

        // --- Controls ---
        uploadNeuroimage: 'Upload Neuroimage (MRI/CT)',
        visualSearch: 'Visual Search',
        readMore: 'Read more',
        noSnippet: 'No snippet available',
        expandingSearch: 'Expanding web search...',
        recoveredSources: 'Recovered Sources',
        primarySources: 'Primary sources',
        backgroundSources: 'Background and guides',
        otherSources: 'Other sources',
        sourceLabel: 'Source',
        typeLabel: 'Type',
        researchArticle: 'Research article',
        healthTopic: 'Health topic',
        otherType: 'Other',

        // --- Theme ---
        switchToLight: 'Switch to light mode',
        switchToDark: 'Switch to dark mode',
        language: 'Language',

        // --- Assessment ---
        assessmentProgress: 'Assessment Progress',
        complete: 'Complete',
        cerebrovascularAssessment: 'Cerebrovascular Assessment',
        basedOnDizziness: 'Based on reported dizziness, please provide specific details.',
        consult: 'Consult',
        assessment: 'Assessment',
        previous: 'Previous',
        continue: 'Continue to Analysis',
    }
};

export const useLanguage = (defaultLang = 'es') => {
    const [lang, setLang] = React.useState(defaultLang);
    const t = (key) => translations[lang]?.[key] || key;
    return { lang, setLang, t };
};