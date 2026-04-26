import React from 'react';

export const SourceCard = ({ title, snippet, score, url }) => {
    return (
        <div className="flex flex-col bg-surface-container-lowest border border-outline-variant/60 rounded-xl p-4 gap-3 hover:border-primary/50 hover:shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all duration-300 transform hover:-translate-y-1 flex-1 w-[280px] shrink-0 group cursor-default">
            <div className="flex justify-between items-start gap-3">
                <div className="flex items-center gap-2 overflow-hidden bg-primary/5 px-2 py-1 rounded-md text-primary group-hover:bg-primary/10 transition-colors">
                    <span className="material-symbols-outlined text-[16px] shrink-0 opacity-70 group-hover:opacity-100 transition-opacity">article</span>
                    <h4 className="font-label-caps text-[11px] font-bold uppercase tracking-wider truncate" title={title}>{title}</h4>
                </div>
                <div className="flex flex-col items-end shrink-0">
                    <span className="text-secondary text-[9px] uppercase tracking-wider mb-0.5">Match</span>
                    <span className="bg-primary-container text-white font-data-tabular text-xs px-2 py-0.5 rounded-md font-bold shadow-sm ring-1 ring-black/5">
                        {score}%
                    </span>
                </div>
            </div>

            <p className="font-body-md text-sm text-on-surface-variant line-clamp-3 leading-relaxed opacity-90 group-hover:opacity-100 transition-opacity">
                {snippet}
            </p>

            {/* Action Buttons (Relevance Feedback & Web Navigation) */}
            <div className="flex items-center justify-between mt-auto pt-3 border-t border-outline-variant/30">
                <a href={url} target="_blank" rel="noreferrer" className="text-xs text-primary font-semibold hover:text-primary-container transition-colors flex items-center gap-1.5 group/link bg-primary/5 px-3 py-1.5 rounded-lg hover:bg-primary/10">
                    Leer más <span className="material-symbols-outlined text-[14px] group-hover/link:translate-x-0.5 transition-transform">arrow_forward</span>
                </a>

                {/* Retroalimentación de relevancia (Feedback Module) */}
                <div className="flex items-center gap-1 bg-surface py-1 px-1.5 rounded-lg border border-outline-variant/30 shadow-sm">
                    <button title="Documento Relevante" className="p-1 px-1.5 text-secondary hover:text-green-600 transition-colors rounded-md hover:bg-green-50">
                        <span className="material-symbols-outlined text-[15px]">thumb_up</span>
                    </button>
                    <button title="No Relevante" className="p-1 px-1.5 text-secondary hover:text-red-600 transition-colors rounded-md hover:bg-red-50">
                        <span className="material-symbols-outlined text-[15px]">thumb_down</span>
                    </button>
                    <div className="w-[1px] h-3.5 bg-outline-variant/50 mx-0.5"></div>
                    <button title="Buscar Similares" className="p-1 px-1.5 text-secondary hover:text-primary transition-colors rounded-md hover:bg-primary/5 flex items-center">
                        <span className="material-symbols-outlined text-[15px]">travel_explore</span>
                    </button>
                </div>
            </div>
        </div>
    );
};