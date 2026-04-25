import React from 'react';
import { Layout } from '../layout/Layout';
import { Message } from './Message';
import { ChatInput } from './ChatInput';

export const ChatView = () => {
    // Mock data to demonstrate RAG, Multimodal, and Web Search Feedback.
    const mockMessages = [
        {
            role: 'assistant',
            content: 'Bienvenido de nuevo, Dr. Julian. Soy el Asistente NeuroMedIR, optimizado para soporte de decisiones clínicas e integración de radiología.\n\nDígame, ¿qué síntomas presenta el paciente o adjunte resultados de neuroimagen para un análisis multimodal preliminar.',
            sources: [],
        },
        {
            role: 'user',
            content: 'Paciente masculino de 45 años. Presenta cefalea en trueno de inicio agudo y leve asimetría facial.\nAdjunto MRI (T2 FLAIR).',
        },
        {
            role: 'assistant',
            content: 'Basado en los síntomas de "cefalea en trueno", asimetría facial, y las características hiperintensas en el corte MRI proporcionado, existe una alta probabilidad de un evento cerebrovascular agudo (posible Hemorragia Subaracnoidea o Isquemia Aguda).\n\nHe recuperado los protocolos clínicos locales y comparado la neuroimagen con nuestra base de datos vectorial (FAISS). Debido a dudas sobre normativas locales vigentes para HSA, he expandido la búsqueda a guías web.',
            usedWebSearch: true,
            multimodalImage: {
                url: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDeFYzzO_5lgC_xYs3cryfHyHPwt4d7kI4N8LtYL0RvWVrV_Xb9uliX-P95Nwo4lKhLzcMjVHWKUhZUKaQU7OBs3Ruaw49Xc2bhdLicUevYBrGivPy5X-GlvLUzCWoznAUkkgde7iFoi77WIYYaFgj_j_xKuzzOoOHPv_WQlCdp4lGclYLg9kxZF75v7mhIKw48Q9v2eAboB9xRBjbxRETT3TbX32Ay0t-Tqh-xNDLeVADO81vcbH7NBULWt7g9Eurg-u0e9QQzUNs4',
                alt: 'MRI Brain Scan',
                caption: 'Vector Similar (Paciente #9102): Hemorragia Subaracnoidea confirmada.',
                score: 91
            },
            sources: [
                {
                    title: 'Protocolo de Ictus Agudo (MinSalud - 2024)',
                    snippet: 'La cefalea en trueno asociada a déficit neurológico focal (como asimetría facial) requiere tomografía computarizada (TC) de cráneo sin contraste en menos de 25 min...',
                    score: 94,
                    url: '#'
                },
                {
                    title: 'AHA/ASA Subarachnoid Hemorrhage Guidelines 2023',
                    snippet: 'Patients presenting with thunderclap headache (TCH) and normal non-contrast CT should undergo lumbar puncture measuring opening pressure and xanthochromia to rule out SAH.',
                    score: 88,
                    url: '#'
                },
                {
                    title: 'Base de Datos Multimodal: FAISS/ResNet',
                    snippet: 'El embedding hiperdenso detectado en cisuras basales coincide en un 91% con el cluster 5 (Hemorragias agudas atípicas).',
                    score: 91,
                    url: '#'
                }
            ]
        }
    ];

    return (
        <Layout>
            <div className="flex-1 overflow-y-auto p-gutter md:p-xl custom-scrollbar pb-32 w-full max-w-5xl mx-auto flex flex-col">
                {/* Date Separator */}
                <div className="flex justify-center mb-8 sticky top-0 z-10 py-2">
                    <span className="font-label-caps text-[10px] text-secondary px-3 py-1 bg-surface-container/80 backdrop-blur-md rounded-full shadow-sm">
                        HOY, 26 DE OCTUBRE
                    </span>
                </div>

                {/* Renderizado de mensajes RAG */}
                {mockMessages.map((msg, idx) => (
                    <Message key={idx} {...msg} />
                ))}

                <div className="h-20 shrink-0"></div>
            </div>

            {/* Componente del Input / Generador de consultas */}
            <ChatInput />
        </Layout>
    );
};