import React from 'react';
import { TopAppBar } from './TopAppBar';

export const Layout = ({ children, showSidebar = true }) => {
    return (
        <div className="h-screen flex flex-col overflow-hidden">
            <TopAppBar />
            <main className="flex-1 flex overflow-hidden relative">
                <section className="flex-1 flex flex-col overflow-hidden relative">
                    {children}
                </section>
            </main>
        </div>
    );
};