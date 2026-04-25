import React from 'react';

export const QuestionCard = ({ icon, title, question, children, footerNote }) => {
    return (
        <section className="bg-surface-container-lowest border border-outline-variant rounded-lg p-lg shadow-[0px_2px_4px_rgba(0,0,0,0.05)] w-full">
            <div className="flex items-center gap-xs mb-md border-b border-primary pb-sm w-fit">
                <span className="material-symbols-outlined text-primary text-[20px]">{icon}</span>
                <h2 className="font-label-caps text-label-caps text-primary uppercase">{title}</h2>
            </div>

            <p className="font-body-lg text-body-lg font-semibold mb-gutter text-on-surface">
                {question}
            </p>

            <div className="w-full">
                {children}
            </div>

            {footerNote && (
                <div className="mt-xl p-md bg-surface-container-low rounded-lg flex items-start gap-md border border-outline-variant/30">
                    <span className="material-symbols-outlined text-error">warning</span>
                    <div>
                        <p className="font-body-sm text-body-sm font-bold text-on-surface">Clinical Note:</p>
                        <p className="font-body-sm text-body-sm text-on-surface-variant">{footerNote}</p>
                    </div>
                </div>
            )}
        </section>
    );
};