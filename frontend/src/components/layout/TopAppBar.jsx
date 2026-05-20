import React, { useContext } from 'react';
import { LanguageContext } from '../../App';
import { ThemeContext } from '../../App';

export const TopAppBar = () => {
  const { lang, setLang, t } = useContext(LanguageContext);
  const { theme, toggleTheme } = useContext(ThemeContext);

  return (
    <header className="flex justify-between items-center w-full px-4 md:px-6 h-16 glass border-b border-slate-200/50 dark:border-slate-700/50 sticky top-0 z-50 shrink-0">
      <div className="flex items-center gap-3">
        {/* Logo con animación */}
        <div className="relative p-2 rounded-xl bg-gradient-to-br from-neurol-500 to-neurol-700 shadow-lg shadow-neurol-500/25 animate-glow">
          <span className="material-symbols-outlined text-white text-xl">neurology</span>
        </div>
        <div className="flex flex-col">
          <span className="text-lg font-bold tracking-tight">
            <span className="text-gradient">Neuro</span>
            <span className="text-slate-700 dark:text-slate-200">MedIR</span>
          </span>
          <span className="text-[9px] font-medium tracking-widest uppercase text-slate-400 dark:text-slate-500 hidden sm:block">
            Medical IR System
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        {/* Language Selector */}
        <div className="flex items-center bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200/60 dark:border-slate-700/40 overflow-hidden">
          <button
            onClick={() => setLang('es')}
            className={`px-3 py-1.5 text-xs font-semibold transition-all duration-200 ${lang === 'es'
              ? 'bg-neurol-500 text-white shadow-sm'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
              }`}
          >
            ES
          </button>
          <button
            onClick={() => setLang('en')}
            className={`px-3 py-1.5 text-xs font-semibold transition-all duration-200 ${lang === 'en'
              ? 'bg-neurol-500 text-white shadow-sm'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
              }`}
          >
            EN
          </button>
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="relative p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200/60 dark:border-slate-700/40 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all duration-300 group"
          title={theme === 'dark' ? t('switchToLight') : t('switchToDark')}
        >
          <span className="material-symbols-outlined text-lg text-amber-500 dark:text-slate-400 group-hover:rotate-180 transition-transform duration-500">
            {theme === 'dark' ? 'light_mode' : 'dark_mode'}
          </span>
        </button>

        {/* Connection Status */}
        <div className="hidden md:flex items-center gap-2 bg-medical-50 dark:bg-medical-500/10 px-3 py-1.5 rounded-xl border border-medical-200/60 dark:border-medical-500/20">
          <div className="w-2 h-2 rounded-full bg-medical-500 animate-pulse-soft" />
          <span className="text-xs font-semibold text-medical-600 dark:text-medical-400">{t('systemConnected')}</span>
        </div>
      </div>
    </header>
  );
};
