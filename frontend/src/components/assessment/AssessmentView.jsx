import React, { useState } from 'react';
import { Layout } from '../layout/Layout';
import { QuestionCard } from './QuestionCard';

export const AssessmentView = () => {
    // Estados interactivos del formulario
    const [onset, setOnset] = useState('sub-acute');
    const [intensity, setIntensity] = useState(7);
    const [signs, setSigns] = useState({
        weakness: true,
        speech: true,
        facial: false,
        visual: false,
        syncope: false
    });

    const handleSignToggle = (signKey) => {
        setSigns(prev => ({ ...prev, [signKey]: !prev[signKey] }));
    };

    const onsetOptions = [
        { id: 'hyper-acute', label: 'Hyper-acute', desc: 'Sudden, within minutes' },
        { id: 'sub-acute', label: 'Sub-acute', desc: 'Developing over hours/days' },
        { id: 'chronic', label: 'Chronic/Intermittent', desc: 'Recurrent episodes' },
        { id: 'progressive', label: 'Progressive', desc: 'Gradually worsening' },
    ];

    return (
        <Layout showSidebar={false}>
            <div className="flex-1 overflow-y-auto px-4 md:px-gutter pt-gutter max-w-4xl mx-auto w-full pb-32 custom-scrollbar">

                {/* Adaptive Progress Bar */}
                <div className="mb-lg">
                    <div className="flex justify-between items-end mb-sm">
                        <p className="font-label-caps text-label-caps text-primary uppercase">Assessment Progress</p>
                        <p className="font-data-tabular text-data-tabular text-secondary">60% Complete</p>
                    </div>
                    <div className="w-full h-2 bg-surface-container rounded-full overflow-hidden">
                        <div className="h-full bg-primary transition-all duration-500" style={{ width: '60%' }}></div>
                    </div>
                    <div className="flex justify-between mt-xs">
                        <div className="flex gap-1">
                            {[1, 2, 3, 4, 5].map(step => (
                                <span key={step} className={`w-2 h-2 rounded-full ${step <= 3 ? 'bg-primary' : 'bg-outline'}`}></span>
                            ))}
                        </div>
                        <p className="font-body-sm text-body-sm text-on-surface-variant">Step 3 of 5</p>
                    </div>
                </div>

                {/* Section Header */}
                <div className="space-y-sm mb-8">
                    <h1 className="font-h2 text-h2 text-on-surface">Cerebrovascular Assessment</h1>
                    <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">
                        Based on the reported dizziness, please provide specific details regarding symptom onset and intensity to determine diagnostic priority.
                    </p>
                </div>

                <div className="space-y-gutter">
                    {/* Form Card 1: Multiple Choice */}
                    <QuestionCard
                        icon="schedule"
                        title="QUESTION 1: TEMPORAL PATTERN"
                        question="Which best describes the onset of your current symptoms?"
                    >
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
                            {onsetOptions.map(option => {
                                const isSelected = onset === option.id;
                                return (
                                    <label
                                        key={option.id}
                                        className={`flex items-center p-md border rounded-lg cursor-pointer transition-all group ${isSelected
                                                ? 'border-primary bg-primary-fixed shadow-sm'
                                                : 'border-outline-variant hover:bg-secondary-fixed hover:border-outline'
                                            }`}
                                    >
                                        <input
                                            type="radio"
                                            name="onset"
                                            value={option.id}
                                            checked={isSelected}
                                            onChange={(e) => setOnset(e.target.value)}
                                            className="w-5 h-5 text-primary focus:ring-primary border-outline-variant cursor-pointer"
                                        />
                                        <div className="ml-md">
                                            <p className={`font-body-md text-body-md font-semibold transition-colors ${isSelected ? 'text-primary' : 'group-hover:text-primary text-on-surface'}`}>
                                                {option.label}
                                            </p>
                                            <p className={`font-body-sm text-body-sm transition-colors ${isSelected ? 'text-on-primary-fixed-variant' : 'text-on-surface-variant'}`}>
                                                {option.desc}
                                            </p>
                                        </div>
                                    </label>
                                );
                            })}
                        </div>
                    </QuestionCard>

                    {/* Form Card 2: Intensity Slider */}
                    <QuestionCard
                        icon="monitor_heart"
                        title="QUESTION 2: INTENSITY SCALE"
                        question="Rate the severity of the neurological deficit (0-10):"
                        footerNote={intensity > 6 ? "Values above 6 require immediate review of the Circle of Willis angiogram." : null}
                    >
                        <div className="px-md">
                            <input
                                type="range"
                                min="0"
                                max="10"
                                value={intensity}
                                onChange={(e) => setIntensity(parseInt(e.target.value))}
                                className="w-full h-2 bg-secondary-fixed rounded-lg appearance-none cursor-pointer accent-primary"
                            />
                            <div className="flex justify-between mt-sm text-on-surface-variant">
                                <span className={`font-data-tabular text-data-tabular ${intensity === 0 ? 'font-bold text-primary' : ''}`}>0 (None)</span>
                                <span className={`font-data-tabular text-data-tabular transition-colors ${intensity > 0 && intensity < 10 ? 'font-bold text-primary' : ''}`}>
                                    {intensity} {intensity > 6 ? '(Severe)' : intensity > 3 ? '(Moderate)' : intensity > 0 ? '(Mild)' : ''}
                                </span>
                                <span className={`font-data-tabular text-data-tabular ${intensity === 10 ? 'font-bold text-error' : ''}`}>10 (Critical)</span>
                            </div>
                        </div>
                    </QuestionCard>

                    {/* Form Card 3: Checkboxes */}
                    <QuestionCard
                        icon="checklist"
                        title="QUESTION 3: ASSOCIATED SIGNS"
                        question="Select all concurrent symptoms present in the last 24 hours:"
                    >
                        <div className="space-y-sm">
                            {[
                                { key: 'weakness', label: 'Unilateral motor weakness' },
                                { key: 'speech', label: 'Speech impairment (Aphasia/Dysarthria)' },
                                { key: 'facial', label: 'Facial asymmetry' },
                                { key: 'visual', label: 'Visual field deficit' },
                                { key: 'syncope', label: 'Syncope' }
                            ].map(sign => (
                                <label
                                    key={sign.key}
                                    className={`flex items-center gap-md p-sm transition-colors rounded cursor-pointer border border-transparent ${signs[sign.key] ? 'bg-primary-fixed/30 border-primary/20' : 'hover:bg-surface-container'
                                        }`}
                                >
                                    <input
                                        type="checkbox"
                                        checked={signs[sign.key]}
                                        onChange={() => handleSignToggle(sign.key)}
                                        className="w-5 h-5 rounded border-outline-variant text-primary focus:ring-primary cursor-pointer transition-all"
                                    />
                                    <span className={`font-body-md text-body-md ${signs[sign.key] ? 'font-medium text-on-primary-fixed-variant' : 'text-on-surface'}`}>
                                        {sign.label}
                                    </span>
                                </label>
                            ))}
                        </div>
                    </QuestionCard>
                </div>

                {/* Navigation Actions */}
                <div className="flex justify-between items-center py-gutter mt-8">
                    <button className="px-xl py-md border border-primary text-primary font-body-md font-semibold rounded-lg hover:bg-blue-50 transition-colors flex items-center gap-sm">
                        <span className="material-symbols-outlined">arrow_back</span>
                        Previous
                    </button>

                    <button className="px-xl py-md bg-primary text-on-primary font-body-md font-semibold rounded-lg shadow-sm hover:bg-primary-container hover:shadow-md transition-all flex items-center gap-sm active:scale-95">
                        Continue to Analysis
                        <span className="material-symbols-outlined">arrow_forward</span>
                    </button>
                </div>

            </div>
        </Layout>
    );
};