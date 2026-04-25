import os

base_dir = r'd:\MATCOM\3er anio\SRI\Proyecto\NeuroMedIR\frontend\src\components'

top_app_bar = """import React from 'react';

export const TopAppBar = () => {
  return (
    <header className="flex justify-between items-center w-full px-4 h-16 max-w-full bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shadow-sm sticky top-0 z-50 shrink-0">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-50 dark:bg-slate-800 hidden md:block">
          <span className="material-symbols-outlined text-blue-700 dark:text-blue-400">clinical_notes</span>
        </div>
        <span className="material-symbols-outlined text-blue-700 dark:text-blue-400 md:hidden">clinical_notes</span>
        <span className="text-lg font-bold text-blue-800 dark:text-blue-300 tracking-tighter">NeuroMedIR</span>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 bg-surface-container/50 px-3 py-1.5 rounded-full border border-outline-variant/30">
           <span className="material-symbols-outlined text-green-500 text-sm">wifi</span>
           <span className="text-xs font-semibold text-secondary">Sistema Conectado</span>
        </div>
      </div>
    </header>
  );
};
"""

chat_input = """import React, { useState } from 'react';

export const ChatInput = ({ onSend, disabled }) => {
  const [text, setText] = useState("");

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSend(text);
      setText("");
    }
  };

  return (
    <div className="absolute bottom-0 left-0 w-full p-md md:p-gutter bg-gradient-to-t from-white via-white/90 to-transparent pb-24 md:pb-gutter z-10">
      <div className={`max-w-3xl mx-auto flex items-end gap-sm bg-white border border-outline shadow-lg rounded-xl p-xs transition-all ${disabled ? 'opacity-50' : 'focus-within:border-primary focus-within:ring-1 focus-within:ring-primary focus-within:shadow-xl'}`}>
        
        <button 
          title="Subir Neuroimagen (MRI/CT)" 
          className="p-sm text-outline hover:text-primary hover:bg-surface-container rounded-lg transition-colors flex items-center justify-center group relative cursor-pointer"
          disabled={disabled}
        >
          <span className="material-symbols-outlined" data-icon="add_photo_alternate">add_photo_alternate</span>
          <span className="absolute -top-10 left-0 bg-inverse-surface text-inverse-on-surface text-[10px] font-label-caps px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
            Búsqueda Visual
          </span>
        </button>

        <textarea 
          className="flex-1 border-none focus:ring-0 font-body-md text-body-md py-sm px-2 resize-none outline-none custom-scrollbar bg-transparent max-h-32" 
          placeholder={disabled ? "Procesando respuesta..." : "Escriba su consulta médica aquí..."}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={disabled}
        />

        <div className="flex items-center gap-xs pr-xs pb-xs shrink-0">
          <button 
            className="bg-primary hover:bg-primary-container text-white p-sm rounded-lg transition-all shadow-md flex items-center justify-center active:scale-95 disabled:bg-gray-400"
            onClick={handleSend}
            disabled={disabled || !text.trim()}
          >
            <span className="material-symbols-outlined" data-icon="send">send</span>
          </button>
        </div>
      </div>
    </div>
  );
};
"""

chat_view = """import React, { useState } from 'react';
import { Layout } from '../layout/Layout';
import { Message } from './Message';
import { ChatInput } from './ChatInput';

export const ChatView = () => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Bienvenido. Soy el Sistema de Recuperación de Información NeuroMedIR.\\n\\nEstoy listo para recibir su consulta médica.',
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
"""

with open(os.path.join(base_dir, 'layout', 'TopAppBar.jsx'), 'w', encoding='utf-8') as f:
    f.write(top_app_bar)

with open(os.path.join(base_dir, 'chat', 'ChatInput.jsx'), 'w', encoding='utf-8') as f:
    f.write(chat_input)

with open(os.path.join(base_dir, 'chat', 'ChatView.jsx'), 'w', encoding='utf-8') as f:
    f.write(chat_view)

print('GUI actualizada correctamente.')
