import React, { useState } from 'react';
import { Layout } from '../layout/Layout';
import { Message } from './Message';
import { ChatInput } from './ChatInput';

export const ChatView = () => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Bienvenido. Soy el Sistema de Recuperación de Información NeuroMedIR.\n\nEstoy listo para recibir su consulta médica.',
      sources: [],
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (text) => {
    if (!text.trim()) return;

    const newUserMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, newUserMsg]);
    setIsLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text })
      });

      if (!res.ok) throw new Error("Error HTTP " + res.status);

      const data = await res.json();

      let asstContent = `Resultados calculados por el motor híbrido (FAISS + BM25).`;

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: asstContent,
        sources: data.results.map(r => ({
          title: r.title,
          snippet: r.snippet || "Sin fragmento",
          score: Math.round(r.score * 100),
          url: r.url || "#"
        })),
        usedWebSearch: data.web_expanded || false
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error de conexión: ${err.message}. Asegúrese de que la base de datos de NeuroMedIR esté corriendo.`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout showSidebar={false}>
      <div className="flex-1 overflow-y-auto p-gutter md:p-xl custom-scrollbar pb-32 w-full max-w-5xl mx-auto flex flex-col">
        <div className="flex justify-center mb-8 sticky top-0 z-10 py-2">
          <span className="font-label-caps text-[10px] text-secondary px-3 py-1 bg-surface-container/80 backdrop-blur-md rounded-full shadow-sm">
            NUEVA SESIÓN MÉDICA
          </span>
        </div>

        {messages.map((msg, idx) => (
          <Message key={idx} {...msg} />
        ))}

        {isLoading && (
          <div className="flex gap-4 w-full max-w-4xl animate-in fade-in duration-300">
            {/* Avatar AI Outline */}
            <div className="w-10 h-10 rounded-xl bg-primary-container/50 animate-pulse flex items-center justify-center shrink-0 border border-primary/10">
              <span className="material-symbols-outlined text-white/50" data-icon="neurology">neurology</span>
            </div>

            <div className="flex flex-col gap-3 flex-1 min-w-0">
              <div className="bg-surface-container-lowest p-4 rounded-2xl rounded-tl-none border border-outline-variant shadow-sm w-full max-w-2xl transform transition-all">
                {/* Skeleton Text */}
                <div className="space-y-3">
                  <div className="h-4 bg-outline-variant/30 rounded-full w-3/4 animate-pulse"></div>
                  <div className="h-4 bg-outline-variant/30 rounded-full w-full animate-pulse delay-75"></div>
                  <div className="h-4 bg-outline-variant/30 rounded-full w-5/6 animate-pulse delay-150"></div>
                </div>
              </div>

              {/* Skeleton Cards Wrapper */}
              <div className="flex gap-3 overflow-x-hidden mt-2">
                {[1, 2].map((i) => (
                  <div key={i} className="flex flex-col bg-surface-container-lowest border border-outline-variant/50 rounded-xl p-3 gap-3 flex-1 min-w-[260px] max-w-[320px] animate-pulse">
                    <div className="flex justify-between items-center">
                      <div className="h-4 bg-outline-variant/30 rounded-full w-1/2"></div>
                      <div className="h-4 w-8 bg-outline-variant/30 rounded-full"></div>
                    </div>
                    <div className="space-y-2 mt-2">
                      <div className="h-3 bg-outline-variant/20 rounded-full w-full"></div>
                      <div className="h-3 bg-outline-variant/20 rounded-full w-4/5"></div>
                      <div className="h-3 bg-outline-variant/20 rounded-full w-full"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="h-20 shrink-0"></div>
      </div>

      <ChatInput onSend={handleSendMessage} disabled={isLoading} />
    </Layout>
  );
};
