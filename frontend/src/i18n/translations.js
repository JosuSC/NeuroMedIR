export const translations = {
    es: {
        // TopAppBar
        systemConnected: 'Sistema Conectado',

        // ChatView
        newMedicalSession: 'NUEVA SESIÓN MÉDICA',
        resultsFromHybrid: 'Resultados calculados por el motor híbrido (FAISS + BM25).',
        connectionError: 'Error de conexión',
        ensureDatabase: 'Asegúrese de que la base de datos de NeuroMedIR esté corriendo.',

        // ChatInput
        uploadNeuroimage: 'Subir Neuroimagen (MRI/CT)',
        visualSearch: 'Búsqueda Visual',
        processingResponse: 'Procesando respuesta...',
        enterMedicalQuery: 'Escriba su consulta médica aquí...',

        // Message
        expandingSearch: 'Información local insuficiente - Ampliando búsqueda en la web...',
        recoveredSources: 'Fuentes Recuperadas (RAG)',
        readMore: 'Leer más',

        // Chat initial message
        welcome: 'Bienvenido. Soy el Sistema de Recuperación de Información NeuroMedIR.\n\nEstoy listo para recibir su consulta médica.',

        // Assessment
        assessmentProgress: 'Assessment Progress',
        complete: 'Complete',
        cerebrovascularAssessment: 'Evaluación Cerebrovascular',
        basedOnDizziness: 'Basado en el mareo reportado, proporcione detalles específicos sobre el inicio de los síntomas e intensidad.',

        // Buttons
        consult: 'Consult',
        assessment: 'Assessment',
        previous: 'Anterior',
        continue: 'Continuar a Análisis',

        // Language selector
        language: 'Idioma',
    },
    en: {
        // TopAppBar
        systemConnected: 'System Connected',

        // ChatView
        newMedicalSession: 'NEW MEDICAL SESSION',
        resultsFromHybrid: 'Results calculated by the hybrid engine (FAISS + BM25).',
        connectionError: 'Connection error',
        ensureDatabase: 'Make sure the NeuroMedIR database is running.',

        // ChatInput
        uploadNeuroimage: 'Upload Neuroimage (MRI/CT)',
        visualSearch: 'Visual Search',
        processingResponse: 'Processing response...',
        enterMedicalQuery: 'Write your medical query here...',

        // Message
        expandingSearch: 'Insufficient local information - Expanding web search...',
        recoveredSources: 'Recovered Sources (RAG)',
        readMore: 'Read more',

        // Chat initial message
        welcome: 'Welcome. I am the NeuroMedIR Information Retrieval System.\n\nI am ready to receive your medical query.',

        // Assessment
        assessmentProgress: 'Assessment Progress',
        complete: 'Complete',
        cerebrovascularAssessment: 'Cerebrovascular Assessment',
        basedOnDizziness: 'Based on reported dizziness, please provide specific details regarding symptom onset and intensity.',

        // Buttons
        consult: 'Consult',
        assessment: 'Assessment',
        previous: 'Previous',
        continue: 'Continue to Analysis',

        // Language selector
        language: 'Language',
    }
};

export const useLanguage = (defaultLang = 'es') => {
    const [lang, setLang] = React.useState(defaultLang);
    const t = (key) => translations[lang]?.[key] || key;
    return { lang, setLang, t };
};
