import React from 'react';
import { TopAppBar } from './TopAppBar';
import { BottomNavBar } from './BottomNavBar';
import { Sidebar } from './Sidebar';

export const Layout = ({ children, showSidebar = true }) => {
    return (
        <div className="bg-surface text-on-surface h-screen flex flex-col overflow-hidden">
            {/* Componente Navbar Superior */}
            <TopAppBar />

            <main className="flex-1 flex overflow-hidden relative">
                {/* Renderizado condicional para vistas como Consult */}
                {showSidebar && <Sidebar />}

                {/* Contenedor principal donde se montan las vistas específicas */}
                <section className="flex-1 flex flex-col bg-white relative overflow-y-auto no-scrollbar">
                    {children}
                </section>
            </main>

            {/* Componente de Navegación Móvil Inferior */}
            <BottomNavBar />
        </div>
    );
};