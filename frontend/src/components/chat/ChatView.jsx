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
          <div className="flex gap-2 items-center text-secondary p-4 animate-pulse">
            <span className="material-symbols-outlined animate-spin">sync</span>
            <span className="text-sm font-semibold">Procesando consulta y recuperando documentos médicos...</span>
          </div>
        )}
        
        <div className="h-20 shrink-0"></div>
      </div>
      
      <ChatInput onSend={handleSendMessage} disabled={isLoading} />
    </Layout>
  );
};
