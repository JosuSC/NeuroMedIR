import React, { useState, useContext } from 'react';
import { LanguageContext } from '../../App';

/**
 * Message — Componente de mensaje del chat.
 *
 * Renderiza diferentes tipos de mensajes según el tipo de respuesta:
 *   - greeting/farewell: Burbuja de texto simple
 *   - question: Respuesta RAG + bibliografía
 *   - symptoms: Texto introductorio + formulario dinámico
 *   - diagnosis: Respuesta + diagnósticos con % + bibliografía
 */
export const Message = ({
    role,
    content,
    type = null,
    diagnoses = null,
    bibliography = null,
    formSchema = null,
    disclaimer = null,
    sources = [],
    usedWebSearch = false,
    onFormSubmit = null,
}) => {
    const isAI = role === 'assistant';
    const { t } = useContext(LanguageContext);

    const classifyCategory = (category) => {
        if (category === 'research_article') return 'research_article';
        if (category === 'health_topic') return 'health_topic';
        return 'other';
    };

    const categoryLabel = (category) => {
        const normalized = classifyCategory(category);
        if (normalized === 'research_article') return t('researchArticle');
        if (normalized === 'health_topic') return t('healthTopic');
        return t('otherType');
    };

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
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neurol-500 to-neurol-700 flex items-center justify-center shrink-0 shadow-lg shadow-neurol-500/20">
                <span className="material-symbols-outlined text-white text-lg">neurology</span>
            </div>

            <div className="flex flex-col gap-3 flex-1 min-w-0">
                {usedWebSearch && (
                    <div className="flex items-center gap-2 text-xs font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 w-fit px-3 py-1.5 rounded-full border border-amber-200/60 dark:border-amber-500/20 animate-fade-in">
                        <span className="material-symbols-outlined text-sm">globe</span>
                        <span>{t('expandingSearch')}</span>
                    </div>
                )}

                {/* Burbuja de contenido principal */}
                <div className="glass-card p-5 shadow-sm rounded-tl-sm">
                    <div className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                        {content}
                    </div>
                </div>

                {/* Formulario de síntomas (type=symptoms) */}
                {formSchema && onFormSubmit && (
                    <SymptomFormInline
                        formSchema={formSchema}
                        onSubmit={onFormSubmit}
                    />
                )}

                {/* Diagnósticos con probabilidades (type=diagnosis) */}
                {diagnoses && diagnoses.length > 0 && (
                    <div className="animate-fade-in" style={{ animationDelay: '0.1s' }}>
                        <div className="flex items-center gap-2 mb-3 pl-2">
                            <span className="material-symbols-outlined text-sm text-medical-500 dark:text-medical-400">monitor_heart</span>
                            <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-medical-500 dark:text-medical-400">
                                {t('possibleDiagnoses')}
                            </span>
                        </div>

                        <div className="space-y-2">
                            {diagnoses.map((diag, idx) => (
                                <div
                                    key={idx}
                                    className="glass-card p-4 flex items-center gap-4 hover:shadow-lg hover:shadow-neurol-500/5 transition-all duration-300"
                                    style={{ animationDelay: `${idx * 0.05}s` }}
                                >
                                    <div className="shrink-0 w-16 flex flex-col items-center">
                                        <span className={`text-lg font-bold ${getProbabilityColor(diag.probability)}`}>
                                            {diag.probability}%
                                        </span>
                                        <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full mt-1 overflow-hidden">
                                            <div
                                                className={`h-full rounded-full transition-all duration-700 ${getProbabilityBarColor(diag.probability)}`}
                                                style={{ width: `${Math.min(diag.probability, 100)}%` }}
                                            />
                                        </div>
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                                            {diag.condition}
                                        </h4>
                                        {diag.supporting_docs && diag.supporting_docs.length > 0 && (
                                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate">
                                                {t('supportedBy')}: {diag.supporting_docs.map(d => d.title).join(', ')}
                                            </p>
                                        )}
                                    </div>

                                    <div className="shrink-0">
                                        <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-1 rounded-md ${getPriorityBadge(diag.probability)}`}>
                                            {getPriorityLabel(diag.probability)}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Bibliografía / Referencias */}
                {bibliography && bibliography.length > 0 && (
                    <div className="animate-fade-in" style={{ animationDelay: '0.2s' }}>
                        <div className="flex items-center gap-2 mb-3 pl-2">
                            <span className="material-symbols-outlined text-sm text-neurol-500 dark:text-neurol-400">menu_book</span>
                            <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-neurol-500 dark:text-neurol-400">
                                {t('bibliography')}
                            </span>
                        </div>

                        {(() => {
                            const primary = bibliography.filter(ref => classifyCategory(ref.category) === 'research_article');
                            const background = bibliography.filter(ref => classifyCategory(ref.category) === 'health_topic');
                            const other = bibliography.filter(ref => classifyCategory(ref.category) === 'other');

                            const sections = [
                                { key: 'primary', label: t('primarySources'), items: primary },
                                { key: 'background', label: t('backgroundSources'), items: background },
                                { key: 'other', label: t('otherSources'), items: other },
                            ].filter(section => section.items.length > 0);

                            return (
                                <div className="glass-card p-4 space-y-4">
                                    {sections.map(section => (
                                        <div key={section.key}>
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[10px] font-bold tracking-[0.12em] uppercase text-slate-500 dark:text-slate-400">
                                                    {section.label}
                                                </span>
                                                <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500">
                                                    {section.items.length}
                                                </span>
                                            </div>

                                            <div className="grid gap-3 md:grid-cols-2">
                                                {section.items.map((ref, idx) => (
                                                    <div key={`${section.key}-${idx}`} className="flex items-start gap-3 group">
                                                        <span className="shrink-0 text-[10px] font-bold text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800 w-6 h-6 rounded-md flex items-center justify-center">
                                                            {ref.ref_num}
                                                        </span>
                                                        <div className="flex-1 min-w-0">
                                                            <a
                                                                href={ref.url}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                className="text-xs font-semibold text-neurol-500 dark:text-neurol-400 hover:text-neurol-700 dark:hover:text-neurol-300 transition-colors"
                                                            >
                                                                {ref.title}
                                                            </a>

                                                            <div className="flex flex-wrap gap-2 mt-1">
                                                                {ref.source && (
                                                                    <span className="text-[9px] font-semibold uppercase tracking-wider px-2 py-1 rounded-md bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                                                                        {t('sourceLabel')}: {ref.source}
                                                                    </span>
                                                                )}
                                                                <span className="text-[9px] font-semibold uppercase tracking-wider px-2 py-1 rounded-md bg-neurol-50 text-neurol-700 dark:bg-neurol-500/10 dark:text-neurol-200">
                                                                    {t('typeLabel')}: {categoryLabel(ref.category)}
                                                                </span>
                                                            </div>

                                                            {ref.snippet && (
                                                                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                                                                    {ref.snippet}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            );
                        })()}
                    </div>
                )}

                {/* Disclaimer médico */}
                {disclaimer && (
                    <div className="animate-fade-in" style={{ animationDelay: '0.3s' }}>
                        <div className="flex items-start gap-2 px-4 py-3 bg-amber-50 dark:bg-amber-500/10 rounded-xl border border-amber-200/60 dark:border-amber-500/20">
                            <span className="material-symbols-outlined text-amber-500 text-sm mt-0.5 shrink-0">warning</span>
                            <p className="text-[11px] text-amber-700 dark:text-amber-300 leading-relaxed">
                                {disclaimer.replace(/\*\*/g, '')}
                            </p>
                        </div>
                    </div>
                )}

                {/* Retro-compatibilidad: fuentes antiguas */}
                {!type && sources.length > 0 && (
                    <div className="mt-1 animate-fade-in" style={{ animationDelay: '0.2s' }}>
                        <div className="flex items-center gap-2 mb-2 pl-2">
                            <span className="material-symbols-outlined text-sm text-neurol-500 dark:text-neurol-400">database</span>
                            <span className="text-[10px] font-bold tracking-[0.15em] uppercase text-neurol-500 dark:text-neurol-400">{t('recoveredSources')}</span>
                        </div>
                        <div className="flex gap-3 overflow-x-auto pb-2 custom-scrollbar snap-x no-scrollbar">
                            {sources.map((source, idx) => (
                                <div className="snap-start" key={idx}>
                                    <SourceCardLegacy {...source} />
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};


// ---------------------------------------------------------------------------
// Formulario de síntomas inline
// ---------------------------------------------------------------------------

const SymptomFormInline = ({ formSchema, onSubmit }) => {
    const { t } = useContext(LanguageContext);

    const initFormData = () => {
        const data = {
            original_query: formSchema.original_query || '',
        };
        (formSchema.fields || []).forEach((field) => {
            if (field.type === 'slider') {
                const min = field.min ?? 1;
                const max = field.max ?? 10;
                const mid = Math.round((min + max) / 2);
                data[field.id] = String(field.default ?? mid);
            } else if (field.type === 'select') {
                data[field.id] = field.default ?? '';
            } else if (field.type === 'multiselect_checkbox') {
                data[field.id] = [];
            } else if (field.type === 'textarea') {
                data[field.id] = '';
            }
        });
        return data;
    };

    const [formData, setFormData] = useState(initFormData);

    const setFieldValue = (fieldId, value) => {
        setFormData(prev => ({ ...prev, [fieldId]: value }));
    };

    const handleSymptomToggle = (fieldId, symptom) => {
        setFormData(prev => {
            const current = prev[fieldId] || [];
            return {
                ...prev,
                [fieldId]: current.includes(symptom)
                    ? current.filter(s => s !== symptom)
                    : [...current, symptom]
            };
        });
    };

    const buildExtraFields = () => {
        const standardIds = new Set([
            'original_query',
            'intensity',
            'duration',
            'dynamic_symptoms',
            'additional_notes',
        ]);
        const extras = [];

        (formSchema.fields || []).forEach((field) => {
            if (standardIds.has(field.id)) {
                return;
            }
            const value = formData[field.id];
            if (field.type === 'multiselect_checkbox' && Array.isArray(value) && value.length > 0) {
                extras.push(`${field.label}: ${value.join(', ')}`);
            } else if (value) {
                extras.push(`${field.label}: ${value}`);
            }
        });

        return extras;
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        const payload = {
            ...formData,
            extra_fields: buildExtraFields(),
        };
        onSubmit(payload);
    };

    return (
        <div className="glass-card p-5 shadow-sm animate-fade-in" style={{ animationDelay: '0.1s' }}>
            <div className="mb-5">
                <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-neurol-500 dark:text-neurol-400 text-lg">clinical_notes</span>
                    <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wide">
                        {formSchema.title || t('fillForm')}
                    </h3>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                    {formSchema.description}
                </p>
            </div>

            {formSchema.detected_symptoms && formSchema.detected_symptoms.length > 0 && (
                <div className="mb-5">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="material-symbols-outlined text-medical-500 text-sm">visibility</span>
                        <span className="text-[10px] font-bold tracking-[0.12em] uppercase text-medical-500 dark:text-medical-400">
                            {t('detectedSymptoms')}
                        </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {formSchema.detected_symptoms.map((symptom, idx) => (
                            <span key={idx} className="bg-medical-50 dark:bg-medical-500/10 text-medical-700 dark:text-medical-300 text-xs font-medium px-3 py-1.5 rounded-lg border border-medical-200/60 dark:border-medical-500/20">
                                {symptom}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
                {formSchema.fields && formSchema.fields.map((field) => (
                    <div key={field.id}>
                        {field.type === 'slider' && (
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                    {field.label}
                                </label>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="range"
                                        min={field.min || 1}
                                        max={field.max || 10}
                                        value={formData[field.id] ?? ''}
                                        onChange={(e) => setFieldValue(field.id, e.target.value)}
                                        className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-neurol-500"
                                    />
                                    <span className="text-lg font-bold text-neurol-500 dark:text-neurol-400 w-8 text-center">
                                        {formData[field.id] ?? ''}
                                    </span>
                                </div>
                                <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                                    <span>{field.min || 1}</span>
                                    <span>{field.max || 10}</span>
                                </div>
                            </div>
                        )}

                        {field.type === 'select' && (
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                    {field.label}
                                </label>
                                <div className="grid grid-cols-1 gap-2">
                                    {field.options && field.options.map((option) => (
                                        <label
                                            key={option}
                                            className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${formData[field.id] === option
                                                ? 'border-neurol-400 dark:border-neurol-500 bg-neurol-50 dark:bg-neurol-500/10'
                                                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                                                }`}
                                        >
                                            <input
                                                type="radio"
                                                name={field.id}
                                                value={option}
                                                checked={formData[field.id] === option}
                                                onChange={(e) => setFieldValue(field.id, e.target.value)}
                                                className="w-4 h-4 text-neurol-500 focus:ring-neurol-500 border-slate-300"
                                            />
                                            <span className="text-sm text-slate-700 dark:text-slate-300">{option}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        )}

                        {field.type === 'multiselect_checkbox' && (
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                    {field.label}
                                </label>
                                {field.hint && (
                                    <p className="text-[10px] text-slate-400 mb-2">{field.hint}</p>
                                )}
                                <div className="grid grid-cols-2 gap-2">
                                    {field.options && field.options.map((option) => {
                                        const current = formData[field.id] || [];
                                        const isSelected = current.includes(option);
                                        return (
                                            <label
                                                key={option}
                                                className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-all text-xs ${isSelected
                                                    ? 'border-neurol-400 dark:border-neurol-500 bg-neurol-50 dark:bg-neurol-500/10 text-neurol-700 dark:text-neurol-300'
                                                    : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'
                                                    }`}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={() => handleSymptomToggle(field.id, option)}
                                                    className="w-3.5 h-3.5 rounded border-slate-300 text-neurol-500 focus:ring-neurol-500"
                                                />
                                                <span className="truncate">{option}</span>
                                            </label>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {field.type === 'textarea' && (
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                    {field.label}
                                </label>
                                <textarea
                                    value={formData[field.id] ?? ''}
                                    onChange={(e) => setFieldValue(field.id, e.target.value)}
                                    placeholder={field.placeholder || t('placeholderNotes')}
                                    rows={3}
                                    className="w-full text-sm border border-slate-200 dark:border-slate-700 rounded-xl p-3 bg-white dark:bg-slate-800/50 text-slate-700 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-neurol-500/30 focus:border-neurol-400 dark:focus:border-neurol-500 outline-none transition-all resize-none"
                                />
                            </div>
                        )}
                    </div>
                ))}

                <button
                    type="submit"
                    className="w-full py-3 px-6 bg-gradient-to-r from-neurol-500 to-neurol-600 hover:from-neurol-600 hover:to-neurol-700 text-white text-sm font-semibold rounded-xl shadow-md shadow-neurol-500/25 hover:shadow-neurol-500/40 transition-all duration-300 flex items-center justify-center gap-2 active:scale-[0.98]"
                >
                    <span className="material-symbols-outlined text-lg">send</span>
                    {t('submitForm')}
                </button>
            </form>
        </div>
    );
};


// ---------------------------------------------------------------------------
// SourceCard legacy (retro-compatibilidad)
// ---------------------------------------------------------------------------

const SourceCardLegacy = ({ title, snippet, score, url }) => {
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
            </div>
        </div>
    );
};


// ---------------------------------------------------------------------------
// Utilidades de estilo para diagnósticos
// ---------------------------------------------------------------------------

const getProbabilityColor = (p) => {
    if (p >= 60) return 'text-red-500 dark:text-red-400';
    if (p >= 30) return 'text-amber-500 dark:text-amber-400';
    if (p >= 15) return 'text-neurol-500 dark:text-neurol-400';
    return 'text-slate-400 dark:text-slate-500';
};

const getProbabilityBarColor = (p) => {
    if (p >= 60) return 'bg-red-500';
    if (p >= 30) return 'bg-amber-500';
    if (p >= 15) return 'bg-neurol-500';
    return 'bg-slate-400';
};

const getPriorityBadge = (p) => {
    if (p >= 60) return 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 border border-red-200/60 dark:border-red-500/20';
    if (p >= 30) return 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-200/60 dark:border-amber-500/20';
    if (p >= 15) return 'bg-neurol-50 dark:bg-neurol-500/10 text-neurol-600 dark:text-neurol-400 border border-neurol-200/60 dark:border-neurol-500/20';
    return 'bg-slate-50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 border border-slate-200/60 dark:border-slate-700/30';
};

const getPriorityLabel = (p) => {
    if (p >= 60) return 'Alta';
    if (p >= 30) return 'Media';
    if (p >= 15) return 'Baja';
    return 'Mínima';
};