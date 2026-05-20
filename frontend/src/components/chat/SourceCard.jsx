import React, { useContext } from 'react';
import { LanguageContext } from '../../App';

export const SourceCard = ({ title, snippet, score, url }) => {
    const { t } = useContext(LanguageContext);

    const getScoreColor = () => {
        if (score >= 80) return 'from-medical-400 to-medical-500';
        if (score >= 50) return 'from-neurol-400 to-neurol-500';
        return 'from-amber-400 to-amber-500';
    };

    return (
        <div className="flex flex-col glass-card p-4 gap-3 hover:shadow-lg hover:shadow-neurol-500/5 transition-all duration-300 transform hover:-translate-y-1 w-[280px] shrink-0 group cursor-default">
            <div className="flex justify-between items-start gap-3">
                <div className="flex items-center gap-2 overflow-hidden bg-neurol-50 dark:bg-neurol-500/10 px-2 py-1 rounded-lg group-hover:bg-neurol-100 dark:group-hover:bg-neurol-500/20 transition-colors">
                    <span className="material-symbols-outlined text-sm text-neurol-500 dark:text-neurol-400 shrink-0">article</span>
                    <h4 className="text-[11px] font-bold uppercase tracking-wider truncate text-neurol-700 dark:text-neurol-300" title={title}>{title}</h4>
                </div>
                <div className="flex flex-col items-end shrink-0">
                    <span className="text-[9px] uppercase tracking-wider mb-0.5 text-slate-400 dark:text-slate-500 font-semibold">Match</span>
                    <span className={`bg-gradient-to-r ${getScoreColor()} text-white text-xs px-2 py-0.5 rounded-md font-bold shadow-sm`}>
                        {score}%
                    </span>
                </div>
            </div>

            <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-3 leading-relaxed group-hover:text-slate-600 dark:group-hover:text-slate-300 transition-colors">
                {snippet}
            </p>

            <div className="flex items-center justify-between mt-auto pt-3 border-t border-slate-100 dark:border-slate-700/40">
                <a href={url} target="_blank" rel="noreferrer" className="text-xs text-neurol-500 dark:text-neurol-400 font-semibold hover:text-neurol-700 dark:hover:text-neurol-300 transition-colors flex items-center gap-1.5 bg-neurol-50 dark:bg-neurol-500/10 px-3 py-1.5 rounded-lg hover:bg-neurol-100 dark:hover:bg-neurol-500/20 group/link">
                    {t('readMore')} <span className="material-symbols-outlined text-sm group-hover/link:translate-x-0.5 transition-transform">arrow_forward</span>
                </a>

                <div className="flex items-center gap-0.5 bg-slate-50 dark:bg-slate-800/50 py-1 px-1.5 rounded-lg border border-slate-200/60 dark:border-slate-700/30">
                    <button title="Relevante" className="p-1 text-slate-400 hover:text-medical-500 transition-colors rounded-md hover:bg-medical-50 dark:hover:bg-medical-500/10">
                        <span className="material-symbols-outlined text-sm">thumb_up</span>
                    </button>
                    <button title="No relevante" className="p-1 text-slate-400 hover:text-red-500 transition-colors rounded-md hover:bg-red-50 dark:hover:bg-red-500/10">
                        <span className="material-symbols-outlined text-sm">thumb_down</span>
                    </button>
                    <button title="Buscar similares" className="p-1 text-slate-400 hover:text-neurol-500 transition-colors rounded-md hover:bg-neurol-50 dark:hover:bg-neurol-500/10">
                        <span className="material-symbols-outlined text-sm">travel_explore</span>
                    </button>
                </div>
            </div>
        </div>
    );
};