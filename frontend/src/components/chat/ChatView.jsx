import React, { useState, useContext, useEffect, useRef } from 'react';
import { Layout } from '../layout/Layout';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { LanguageContext } from '../../App';

export const ChatView = () => {
  const { t } = useContext(LanguageContext);
  const messagesEndRef = useRef(null);

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: t('welcome'),
      sources: [],
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [isBackendReady, setIsBackendReady] = useState(false);

  // Auto-scroll al último mensaje
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/health');
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
      const res = await fetch('http://localhost:8000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text })
      });

      if (!res.ok) throw new Error("Error HTTP " + res.status);
      const data = await res.json();

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: t('resultsFromHybrid'),
        sources: data.results.map(r => ({
          title: r.title,
          snippet: r.snippet || t('noSnippet'),
          score: Math.round(r.score * 100),
          url: r.url || "#"
        })),
        usedWebSearch: data.web_expanded || false
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `${t('connectionError')}: ${err.message}. ${t('ensureDatabase')}`
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout showSidebar={false}>
      <div className="flex-1 overflow-y-auto p-4 md:p-6 custom-scrollbar w-full max-w-5xl mx-auto flex flex-col">
        {/* Session badge */}
        <div className="flex justify-center mb-6 py-2 animate-fade-in">
          <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-neurol-500 dark:text-neurol-400 px-4 py-1.5 glass-card shadow-sm">
            {t('newMedicalSession')}
          </span>
        </div>

        {/* Messages */}
        {messages.map((msg, idx) => (
          <div key={idx} style={{ animationDelay: `${idx * 0.05}s` }}>
            <Message {...msg} />
          </div>
        ))}

        {/* Loading skeleton */}
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
              <div className="flex gap-3 overflow-x-hidden mt-2">
                {[1, 2].map((i) => (
                  <div key={i} className="glass-card p-4 gap-3 min-w-[260px] max-w-[320px] animate-shimmer bg-[length:200%_100%]">
                    <div className="flex justify-between items-center">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700/50 rounded-full w-1/2"></div>
                      <div className="h-4 w-8 bg-slate-200 dark:bg-slate-700/50 rounded-full"></div>
                    </div>
                    <div className="space-y-2 mt-3">
                      <div className="h-3 bg-slate-200 dark:bg-slate-700/50 rounded-full w-full"></div>
                      <div className="h-3 bg-slate-200 dark:bg-slate-700/50 rounded-full w-4/5"></div>
                    </div>
                  </div>
                ))}
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