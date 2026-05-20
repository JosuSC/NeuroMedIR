import React, { useState, useContext, useRef } from 'react';
import { LanguageContext } from '../../App';

export const ChatInput = ({ onSend, disabled, isBackendReady = true }) => {
  const [text, setText] = useState("");
  const { t } = useContext(LanguageContext);
  const textareaRef = useRef(null);

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSend(text);
      setText("");
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleTextChange = (e) => {
    setText(e.target.value);
    // Auto-resize
    const ta = e.target;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 128) + 'px';
  };

  const getPlaceholder = () => {
    if (!isBackendReady) return t('connectingEngines');
    return disabled ? t('processingResponse') : t('enterMedicalQuery');
  };

  return (
    <div className="w-full px-4 md:px-6 pb-4 pt-2 z-50 shrink-0">
      <div className={`max-w-3xl mx-auto flex items-end gap-2 glass-card px-3 py-2 shadow-lg transition-all duration-300 ${disabled ? 'opacity-50' : 'focus-within:shadow-neurol-500/10 focus-within:border-neurol-400/50 dark:focus-within:border-neurol-500/50 focus-within:shadow-xl'
        }`}>
        <button
          title={t('uploadNeuroimage')}
          className="p-2 text-slate-400 hover:text-neurol-500 hover:bg-neurol-50 dark:hover:bg-neurol-500/10 rounded-lg transition-all duration-200 flex items-center justify-center group relative cursor-pointer"
          disabled={disabled}
        >
          <span className="material-symbols-outlined text-xl">add_photo_alternate</span>
          <span className="absolute -top-9 left-0 bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-800 text-[10px] font-semibold px-2 py-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-lg">
            {t('visualSearch')}
          </span>
        </button>

        <textarea
          ref={textareaRef}
          className="flex-1 border-none focus:ring-0 py-2 px-2 resize-none outline-none custom-scrollbar bg-transparent max-h-32 text-sm text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
          placeholder={getPlaceholder()}
          rows={1}
          value={text}
          onChange={handleTextChange}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={disabled}
        />

        <button
          className={`p-2.5 rounded-xl transition-all duration-300 flex items-center justify-center shadow-md ${text.trim() && !disabled
              ? 'bg-gradient-to-r from-neurol-500 to-neurol-600 hover:from-neurol-600 hover:to-neurol-700 text-white shadow-neurol-500/25 hover:shadow-neurol-500/40 active:scale-95'
              : 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 shadow-none cursor-not-allowed'
            }`}
          onClick={handleSend}
          disabled={disabled || !text.trim()}
        >
          <span className="material-symbols-outlined text-xl">send</span>
        </button>
      </div>
    </div>
  );
};