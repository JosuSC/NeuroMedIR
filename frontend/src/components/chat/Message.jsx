import React, { useContext } from 'react';
import { SourceCard } from './SourceCard';
import { LanguageContext } from '../../App';

export const Message = ({ role, content, sources = [], multimodalImage = null, usedWebSearch = false }) => {
    const isAI = role === 'assistant';
    const { t } = useContext(LanguageContext);

    if (!isAI) {
        return (
            <div className="flex justify-end mb-6 w-full animate-fade-in-up">
                <div className="bg-gradient-to-br from-neurol-500 to-neurol-700 text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-2xl shadow-lg shadow-neurol-500/20">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex gap-4 max-w-4xl mb-8 w-full animate-fade-in-up">
            {/* AI Avatar */}
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neurol-500 to-neurol-700 flex items-center justify-center shrink-0 shadow-lg shadow-neurol-500/20">
                <span className="material-symbols-outlined text-white text-lg">neurology</span>
            </div>

            <div className="flex flex-col gap-2 flex-1 min-w-0">
                {/* Web search indicator */}
                {usedWebSearch && (
                    <div className="flex items-center gap-2 text-xs font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 w-fit px-3 py-1.5 rounded-full border border-amber-200/60 dark:border-amber-500/20 animate-fade-in">
                        <span className="material-symbols-outlined text-sm">globe</span>
                        <span>{t('expandingSearch')}</span>
                    </div>
                )}

                {/* Content bubble */}
                <div className="glass-card p-5 shadow-sm rounded-tl-sm">
                    <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                        {content}
                    </p>

                    {multimodalImage && (
                        <div className="mt-4 rounded-xl overflow-hidden border border-slate-200/60 dark:border-slate-700/30 group relative max-w-sm cursor-pointer shadow-sm hover:shadow-md transition-shadow">
                            <img
                                src={multimodalImage.url}
                                alt={multimodalImage.alt}
                                className="w-full h-auto object-cover max-h-[250px] transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-3">
                                <p className="text-white text-xs tracking-wide">{multimodalImage.caption}</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Source cards */}
                {sources.length > 0 && (
                    <div className="mt-1 animate-fade-in" style={{ animationDelay: '0.2s' }}>
                        <div className="flex items-center gap-2 mb-2 pl-2">
                            <span className="material-symbols-outlined text-sm text-neurol-500 dark:text-neurol-400">database</span>
                            <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-neurol-500 dark:text-neurol-400">{t('recoveredSources')}</span>
                        </div>

                        <div className="flex gap-3 overflow-x-auto pb-2 custom-scrollbar snap-x no-scrollbar">
                            {sources.map((source, idx) => (
                                <div className="snap-start" key={idx}>
                                    <SourceCard {...source} />
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};