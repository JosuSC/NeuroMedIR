import React, { useState, useEffect } from 'react'
import { ChatView } from './components/chat/ChatView'
import { translations } from './i18n/translations'

export const LanguageContext = React.createContext()
export const ThemeContext = React.createContext()

function App() {
    const [lang, setLang] = useState('es')
    const [theme, setTheme] = useState(() => {
        if (typeof window !== 'undefined') {
            return localStorage.getItem('neuromedir-theme') || 'dark'
        }
        return 'dark'
    })

    const t = (key) => translations[lang]?.[key] || key

    useEffect(() => {
        const root = document.documentElement
        root.classList.toggle('dark', theme === 'dark')
        localStorage.setItem('neuromedir-theme', theme)
    }, [theme])

    const toggleTheme = () => {
        setTheme(prev => prev === 'dark' ? 'light' : 'dark')
    }

    return (
        <LanguageContext.Provider value={{ lang, setLang, t }}>
            <ThemeContext.Provider value={{ theme, toggleTheme }}>
                <div className="relative min-h-screen overflow-hidden">
                    {/* Animated background orbs */}
                    <div className="fixed inset-0 -z-10 overflow-hidden">
                        <div className="absolute -top-40 -right-40 w-96 h-96 bg-neurol-500/10 dark:bg-neurol-500/5 rounded-full blur-3xl animate-float" />
                        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-medical-500/10 dark:bg-medical-500/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
                        <div className="absolute -bottom-40 right-1/3 w-72 h-72 bg-neurol-400/8 dark:bg-neurol-400/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '4s' }} />
                        {/* Grid pattern overlay */}
                        <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] dark:bg-[linear-gradient(rgba(99,102,241,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.05)_1px,transparent_1px)] bg-[size:60px_60px]" />
                    </div>

                    <ChatView />
                </div>
            </ThemeContext.Provider>
        </LanguageContext.Provider>
    )
}

export default App