import React, { useState } from 'react';

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
