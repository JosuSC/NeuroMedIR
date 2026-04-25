import React from 'react';

export const SourceCard = ({ title, snippet, score, url }) => {
    return (
        <div className="flex flex-col bg-surface-container-lowest border border-outline-variant rounded-lg p-3 gap-2 hover:border-primary hover:shadow-md transition-all flex-1 min-w-[260px] max-w-[320px] shrink-0 group">
            <div className="flex justify-between items-start gap-2">
                <div className="flex items-center gap-1.5 overflow-hidden">
                    <span className="material-symbols-outlined text-[16px] text-primary shrink-0 opacity-70 group-hover:opacity-100 transition-opacity">article</span>
                    <h4 className="font-label-caps text-label-caps text-on-surface truncate" title={title}>{title}</h4>
                </div>
                <span className="bg-primary-container text-on-primary-container font-data-tabular text-[10px] px-2 py-0.5 rounded-full shrink-0 font-bold tracking-wide">
                    {score}%
                </span>
            </div>

            <p className="font-body-sm text-[12px] text-on-surface-variant line-clamp-3 leading-relaxed">
                {snippet}
            </p>

            {/* Step 3: Action Buttons (Relevance Feedback & Web Navigation) */}
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-outline-variant/60">
                <a href={url} target="_blank" rel="noreferrer" className="text-[10px] text-primary font-bold hover:underline flex items-center gap-1">
                    Ver Fuente <span className="material-symbols-outlined text-[12px]">open_in_new</span>
                </a>

                {/* Retroalimentación de relevancia (Feedback Module) */}
                <div className="flex items-center gap-0.5 bg-surface-container px-1 py-0.5 rounded-md">
                    <button title="Documento Relevante" className="p-1 text-on-surface-variant hover:text-primary transition-colors rounded hover:bg-white/80">
                        <span className="material-symbols-outlined text-[14px]">thumb_up</span>
                    </button>
                    <button title="No Relevante" className="p-1 text-on-surface-variant hover:text-error transition-colors rounded hover:bg-white/80">
                        <span className="material-symbols-outlined text-[14px]">thumb_down</span>
                    </button>
                    <div className="w-[1px] h-3 bg-outline/30 mx-1"></div>
                    <button title="Buscar Similares" className="p-1 text-on-surface-variant hover:text-primary transition-colors rounded hover:bg-white/80 flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">travel_explore</span>
                    </button>
                </div>
            </div>
        </div>
    );
};