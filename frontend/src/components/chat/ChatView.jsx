import React, { useState, useContext, useEffect, useRef } from 'react';
import { Layout } from '../layout/Layout';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { LanguageContext } from '../../App';

const API_BASE = 'http://localhost:8000';

/**
 * ChatView — Vista principal del chat conversacional NeuroMedIR.
 *
 * Flujo:
 *   1. Usuario escribe mensaje → POST /api/chat
 *   2. Backend clasifica intención (saludo/pregunta/síntomas/despedida)
 *   3. Según tipo:
 *      - SALUDO/DESPEDIDA → Respuesta conversacional directa
 *      - PREGUNTA → Respuesta RAG + bibliografía
 *      - SÍNTOMAS → Formulario dinámico → Diagnóstico + bibliografía
 *   4. Si se genera formulario → usuario rellena → POST /api/chat/submit_form
 */
export const ChatView = () => {
  const { t } = useContext(LanguageContext);
  const messagesEndRef = useRef(null);

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: t('welcome'),
      type: 'greeting',
      diagnoses: null,
      bibliography: null,
      formSchema: null,
      disclaimer: null,
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [isBackendReady, setIsBackendReady] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) {
          setIsBackendReady(true);
        } else {
          setTimeout(checkHealth, 2000);
        }
      } catch (err) {
        setTimeout(checkHealth, 2000);
      }
    };
    checkHealth();
  }, []);

  const handleSendMessage = async (text) => {
    if (!text.trim()) return;

    const newUserMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, newUserMsg]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });

      if (!res.ok) throw new Error("Error HTTP " + res.status);
      const data = await res.json();

      const assistantMsg = {
        role: 'assistant',
        content: data.message || '',
        type: data.type,
        diagnoses: data.diagnoses || null,
        bibliography: data.bibliography || null,
        formSchema: data.form_schema || null,
        disclaimer: data.disclaimer || null,
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `${t('connectionError')}: ${err.message}. ${t('ensureDatabase')}`,
        type: 'error',
        diagnoses: null,
        bibliography: null,
        formSchema: null,
        disclaimer: null,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = async (formData) => {
    setIsLoading(true);

    const submittedSymptoms = [
      formData.intensity && `Intensidad: ${formData.intensity}/10`,
      formData.duration && `Duración: ${formData.duration}`,
      formData.dynamic_symptoms?.length > 0 && `Síntomas adicionales: ${formData.dynamic_symptoms.join(', ')}`,
      formData.additional_notes && `Notas: ${formData.additional_notes}`,
    ].filter(Boolean).join(' | ');

    setMessages(prev => [...prev, {
      role: 'user',
      content: `📋 Formulario completado — ${submittedSymptoms}`,
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/chat/submit_form`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (!res.ok) throw new Error("Error HTTP " + res.status);
      const data = await res.json();

      const assistantMsg = {
        role: 'assistant',
        content: data.message || '',
        type: data.type || 'diagnosis',
        diagnoses: data.diagnoses || null,
        bibliography: data.bibliography || null,
        formSchema: null,
        disclaimer: data.disclaimer || null,
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `${t('connectionError')}: ${err.message}. ${t('ensureDatabase')}`,
        type: 'error',
        diagnoses: null,
        bibliography: null,
        formSchema: null,
        disclaimer: null,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout showSidebar={false}>
      <div className="flex-1 overflow-y-auto p-4 md:p-6 custom-scrollbar w-full max-w-5xl mx-auto flex flex-col">
        <div className="flex justify-center mb-6 py-2 animate-fade-in">
          <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-neurol-500 dark:text-neurol-400 px-4 py-1.5 glass-card shadow-sm">
            {t('newMedicalSession')}
          </span>
        </div>

        {messages.map((msg, idx) => (
          <div key={idx} style={{ animationDelay: `${idx * 0.05}s` }}>
            <Message
              {...msg}
              onFormSubmit={handleFormSubmit}
            />
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-4 w-full max-w-4xl animate-fade-in">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neurol-500 to-neurol-700 flex items-center justify-center shrink-0 animate-pulse-soft shadow-lg shadow-neurol-500/20">
              <span className="material-symbols-outlined text-white text-lg">neurology</span>
            </div>
            <div className="flex flex-col gap-3 flex-1 min-w-0">
              <div className="glass-card p-5 shadow-sm w-full max-w-2xl">
                <div className="space-y-3">
                  <div className="h-4 bg-slate-200 dark:bg-slate-700/50 rounded-full w-3/4 animate-shimmer bg-[length:200%_100%]"></div>
                  <div className="h-4 bg-slate-200 dark:bg-slate-700/50 rounded-full w-full animate-shimmer bg-[length:200%_100%]" style={{ animationDelay: '0.2s' }}></div>
                  <div className="h-4 bg-slate-200 dark:bg-slate-700/50 rounded-full w-5/6 animate-shimmer bg-[length:200%_100%]" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} className="h-24 shrink-0" />
      </div>

      <ChatInput onSend={handleSendMessage} disabled={isLoading || !isBackendReady} isBackendReady={isBackendReady} />
    </Layout>
  );
};