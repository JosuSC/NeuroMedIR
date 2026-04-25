import React from 'react';

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
