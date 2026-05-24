/**
 * SymptomForm — Componente de formulario de síntomas para NeuroMedIR.
 * Componente reutilizable que renderiza un formulario dinámico
 * basado en el esquema JSON generado por el backend.
 */

import React, { useState, useContext } from 'react';
import { LanguageContext } from '../../App';

export const SymptomForm = ({ formSchema, onSubmit }) => {
    const { t } = useContext(LanguageContext);

    const [formData, setFormData] = useState({
        original_query: formSchema?.original_query || '',
        intensity: '5',
        duration: '',
        dynamic_symptoms: [],
        additional_notes: '',
    });

    const handleIntensityChange = (value) => {
        setFormData(prev => ({ ...prev, intensity: value }));
    };

    const handleDurationChange = (value) => {
        setFormData(prev => ({ ...prev, duration: value }));
    };

    const handleSymptomToggle = (symptom) => {
        setFormData(prev => ({
            ...prev,
            dynamic_symptoms: prev.dynamic_symptoms.includes(symptom)
                ? prev.dynamic_symptoms.filter(s => s !== symptom)
                : [...prev.dynamic_symptoms, symptom]
        }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (onSubmit) onSubmit(formData);
    };

    if (!formSchema) return null;

    return (
        <div className="glass-card p-5 shadow-sm">
            <div className="mb-5">
                <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-neurol-500 text-lg">clinical_notes</span>
                    <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wide">
                        {formSchema.title || t('fillForm')}
                    </h3>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                    {formSchema.description}
                </p>
            </div>

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
                                        value={formData.intensity}
                                        onChange={(e) => handleIntensityChange(e.target.value)}
                                        className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-neurol-500"
                                    />
                                    <span className="text-lg font-bold text-neurol-500 w-8 text-center">
                                        {formData.intensity}
                                    </span>
                                </div>
                            </div>
                        )}

                        {field.type === 'select' && (
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                    {field.label}
                                </label>
                                <div className="space-y-2">
                                    {field.options && field.options.map((option) => (
                                        <label
                                            key={option}
                                            className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${formData.duration === option
                                                    ? 'border-neurol-400 bg-neurol-50'
                                                    : 'border-slate-200 hover:border-slate-300'
                                                }`}
                                        >
                                            <input
                                                type="radio"
                                                name="duration"
                                                value={option}
                                                checked={formData.duration === option}
                                                onChange={(e) => handleDurationChange(e.target.value)}
                                                className="w-4 h-4 text-neurol-500"
                                            />
                                            <span className="text-sm text-slate-700">{option}</span>
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
                                {field.hint && <p className="text-[10px] text-slate-400 mb-2">{field.hint}</p>}
                                <div className="grid grid-cols-2 gap-2">
                                    {field.options && field.options.map((option) => {
                                        const isSelected = formData.dynamic_symptoms.includes(option);
                                        return (
                                            <label
                                                key={option}
                                                className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-all text-xs ${isSelected
                                                        ? 'border-neurol-400 bg-neurol-50 text-neurol-700'
                                                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                                                    }`}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={() => handleSymptomToggle(option)}
                                                    className="w-3.5 h-3.5 rounded text-neurol-500"
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
                                    value={formData.additional_notes}
                                    onChange={(e) => setFormData(prev => ({ ...prev, additional_notes: e.target.value }))}
                                    placeholder={field.placeholder || ''}
                                    rows={3}
                                    className="w-full text-sm border border-slate-200 rounded-xl p-3 bg-white text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:ring-neurol-500/30 focus:border-neurol-400 outline-none transition-all resize-none"
                                />
                            </div>
                        )}
                    </div>
                ))}

                <button
                    type="submit"
                    className="w-full py-3 px-6 bg-gradient-to-r from-neurol-500 to-neurol-600 hover:from-neurol-600 hover:to-neurol-700 text-white text-sm font-semibold rounded-xl shadow-md transition-all duration-300 flex items-center justify-center gap-2 active:scale-[0.98]"
                >
                    <span className="material-symbols-outlined text-lg">send</span>
                    {t('submitForm')}
                </button>
            </form>
        </div>
    );
};

