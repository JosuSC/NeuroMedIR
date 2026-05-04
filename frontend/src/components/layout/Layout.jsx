import React from 'react';
import { TopAppBar } from './TopAppBar';

export const Layout = ({ children, showSidebar = true }) => {
    return (
        <div className="bg-surface text-on-surface h-screen flex flex-col overflow-hidden">
            {/* Componente Navbar Superior */}
            <TopAppBar />

            <main className="flex-1 flex overflow-hidden relative">
                {/* Contenedor principal donde se montan las vistas específicas */}
                <section className="flex-1 flex flex-col bg-white overflow-hidden relative">
                    {children}
                </section>
            </main>
        </div>
    );
};