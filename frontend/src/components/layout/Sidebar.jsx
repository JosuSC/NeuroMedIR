import React from 'react';

export const Sidebar = () => {
    return (
        <aside className="hidden lg:flex flex-col w-72 border-r border-outline-variant bg-surface-container-low p-gutter shrink-0">
            <div className="mb-gutter">
                <h3 className="font-h3 text-h3 text-primary mb-sm">Recent Cases</h3>
                <p className="font-body-sm text-body-sm text-on-surface-variant">Your diagnostic history</p>
            </div>

            <div className="flex-1 overflow-y-auto space-y-md custom-scrollbar pr-2">
                <div className="p-md rounded-lg bg-white border border-outline-variant shadow-sm hover:border-primary transition-all cursor-pointer">
                    <span className="font-label-caps text-label-caps text-primary block mb-xs">PATIENT #8821</span>
                    <p className="font-body-sm text-body-sm font-semibold text-on-surface truncate">Acute Hemispheric Syndrome</p>
                    <p className="font-body-sm text-body-sm text-secondary mt-xs">2 hours ago</p>
                </div>

                <div className="p-md rounded-lg bg-white/50 border border-transparent hover:bg-white hover:border-outline-variant transition-all cursor-pointer">
                    <span className="font-label-caps text-label-caps text-secondary block mb-xs">PATIENT #7743</span>
                    <p className="font-body-sm text-body-sm text-on-surface truncate">Transient Ischemic Attack</p>
                    <p className="font-body-sm text-body-sm text-secondary mt-xs">Yesterday</p>
                </div>

                <div className="p-md rounded-lg bg-white/50 border border-transparent hover:bg-white hover:border-outline-variant transition-all cursor-pointer">
                    <span className="font-label-caps text-label-caps text-secondary block mb-xs">PATIENT #9102</span>
                    <p className="font-body-sm text-body-sm text-on-surface truncate">Subarachnoid Hemorrhage</p>
                    <p className="font-body-sm text-body-sm text-secondary mt-xs">Oct 24, 2023</p>
                </div>
            </div>

            <button className="mt-gutter flex items-center justify-center gap-sm bg-secondary-container text-on-secondary-container py-md rounded-lg font-semibold hover:bg-secondary-fixed transition-all w-full">
                <span className="material-symbols-outlined text-[20px]">add</span>
                <span className="font-body-sm text-body-sm">New Consultation</span>
            </button>
        </aside>
    );
};