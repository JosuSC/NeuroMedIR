import React from 'react';
import { SourceCard } from './SourceCard';

export const Message = ({ role, content, sources = [], multimodalImage = null, usedWebSearch = false }) => {
    const isAI = role === 'assistant';

    if (!isAI) {
        return (
            <div className="flex justify-end mb-6 w-full">
                <div className="bg-primary text-on-primary p-md rounded-2xl rounded-tr-none max-w-2xl shadow-sm relative">
                    <p className="font-body-md text-body-md whitespace-pre-wrap">{content}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex gap-md max-w-4xl mb-10 w-full animate-fade-in-up">
            {/* Botón de IA / Avatar */}
            <div className="w-10 h-10 rounded-lg bg-primary-container flex items-center justify-center shrink-0 shadow-sm border border-primary/20">
                <span className="material-symbols-outlined text-white" data-icon="neurology">neurology</span>
            </div>

            <div className="flex flex-col gap-2 flex-1 min-w-0">
                {/* Step 3: Web Search Feedback Indicator */}
                {usedWebSearch && (
                    <div className="flex items-center gap-2 text-xs font-label-caps text-secondary bg-surface-container-high w-fit px-3 py-1.5 rounded-full border border-outline-variant shadow-sm animate-pulse">
                        <span className="material-symbols-outlined text-[14px] text-primary">globe</span>
                        <span>Información local insuficiente - Ampliando búsqueda en la web...</span>
                    </div>
                )}

                <div className="bg-surface-container-lowest p-md rounded-2xl rounded-tl-none border border-outline-variant shadow-sm">
                    {/* Text Content */}
                    <p className="font-body-md text-body-md text-on-surface leading-relaxed whitespace-pre-wrap">
                        {content}
                    </p>

                    {/* Step 2: Multimodal Image Retrieval rendering */}
                    {multimodalImage && (
                        <div className="mt-4 rounded-xl overflow-hidden border border-outline-variant group relative max-w-sm cursor-pointer shadow-sm hover:shadow-md transition-shadow">
                            <img
                                src={multimodalImage.url}
                                alt={multimodalImage.alt}
                                className="w-full h-auto object-cover max-h-[250px] transition-transform duration-500 group-hover:scale-105"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-3">
                                <p className="text-white text-xs font-body-sm tracking-wide">{multimodalImage.caption}</p>
                            </div>
                            <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm text-white text-[10px] px-2 py-1 rounded-md font-label-caps flex items-center gap-1 border border-white/20">
                                <span className="material-symbols-outlined text-[12px] text-green-400">center_focus_strong</span>
                                {multimodalImage.score}% Visual Match
                            </div>
                        </div>
                    )}
                </div>

                {/* Step 2: RAG Source Cards Container */}
                {sources.length > 0 && (
                    <div className="mt-1">
                        <div className="flex items-center gap-2 mb-2 pl-2">
                            <span className="material-symbols-outlined text-[14px] text-secondary">database</span>
                            <span className="font-label-caps text-[10px] text-secondary uppercase tracking-wider">Fuentes Recuperadas (RAG)</span>
                        </div>

                        <div className="flex gap-3 overflow-x-auto pb-2 custom-scrollbar snap-x no-scrollbar-on-mobile">
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