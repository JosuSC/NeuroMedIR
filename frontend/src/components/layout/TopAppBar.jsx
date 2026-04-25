import React from 'react';

export const TopAppBar = () => {
    return (
        <header className="flex justify-between items-center w-full px-4 h-16 max-w-full bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shadow-sm sticky top-0 z-50 shrink-0">
            <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-50 dark:bg-slate-800 hidden md:block">
                    <span className="material-symbols-outlined text-blue-700 dark:text-blue-400">clinical_notes</span>
                </div>
                <span className="material-symbols-outlined text-blue-700 dark:text-blue-400 md:hidden">clinical_notes</span>
                <span className="text-lg font-bold text-blue-800 dark:text-blue-300 tracking-tighter">NeuroMedIR</span>
            </div>

            <div className="flex items-center gap-4">
                <div className="hidden md:flex items-center gap-6 mr-6">
                    <a className="font-sans text-sm font-semibold tracking-wide text-blue-700 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors px-3 py-2 rounded" href="#">Consult</a>
                    <a className="font-sans text-sm font-semibold tracking-wide text-slate-500 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors px-3 py-2 rounded" href="#">Assessment</a>
                    <a className="font-sans text-sm font-semibold tracking-wide text-slate-500 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors px-3 py-2 rounded" href="#">Analysis</a>
                    <a className="font-sans text-sm font-semibold tracking-wide text-slate-500 dark:text-slate-400 hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors px-3 py-2 rounded" href="#">History</a>
                </div>

                <div className="flex items-center gap-3">
                    <span className="hidden lg:block text-slate-500 font-sans text-sm font-semibold tracking-wide">Dr. Julian</span>
                    <img
                        alt="User Physician Profile"
                        className="w-10 h-10 rounded-full border-2 border-primary-container object-cover"
                        src="https://lh3.googleusercontent.com/aida-public/AB6AXuDsPajRafFhTrq4oje5U-SeuFTww_W70gq4o4bMrZgsmITagizz1PMpqE0WzS3j1-3nfN6vzaC10oPgrSkRtoVnWXNydm7DTn6Zg9lKuXDbKuWwGY-EfI6cdoo2QECtDmRALCggZXLw4gABpjBibcXJfu3dvKRfpVkz3vqGDcr6yKgMavjiqZrH9zQNEXzKBOdVMoDIF1aNoldWdwdJ7_DIXG6Ahy41VsoYnvqsBDrCjJhNVWb8WQh-AiEP7biWb6uJFGmu3yYEHSF3"
                    />
                </div>
            </div>
        </header>
    );
};