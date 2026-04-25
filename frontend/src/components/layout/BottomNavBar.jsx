import React from 'react';

export const BottomNavBar = () => {
    return (
        <nav className="md:hidden flex shrink-0 justify-around items-center bg-white dark:bg-slate-950 px-2 h-16 shadow-[0_-2px_10px_rgba(0,0,0,0.05)] border-t border-slate-200 dark:border-slate-800 w-full z-50">
            <a className="flex flex-col items-center justify-center text-blue-700 dark:text-blue-400 border-t-2 border-blue-700 dark:border-blue-400 pt-2 pb-1 transition-all flex-1" href="#consult">
                <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>chat_bubble</span>
                <span className="text-[11px] font-medium font-sans uppercase tracking-wider">Consult</span>
            </a>
            <a className="flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 pt-2 pb-1 hover:text-blue-600 transition-all flex-1" href="#assessment">
                <span className="material-symbols-outlined">dynamic_form</span>
                <span className="text-[11px] font-medium font-sans uppercase tracking-wider">Assessment</span>
            </a>
            <a className="flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 pt-2 pb-1 hover:text-blue-600 transition-all flex-1" href="#analysis">
                <span className="material-symbols-outlined">analytics</span>
                <span className="text-[11px] font-medium font-sans uppercase tracking-wider">Analysis</span>
            </a>
            <a className="flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 pt-2 pb-1 hover:text-blue-600 transition-all flex-1" href="#history">
                <span className="material-symbols-outlined">history</span>
                <span className="text-[11px] font-medium font-sans uppercase tracking-wider">History</span>
            </a>
        </nav>
    );
};