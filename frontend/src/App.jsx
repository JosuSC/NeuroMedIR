import React, { useState } from 'react'
import { ChatView } from './components/chat/ChatView'
import { translations } from './i18n/translations'

export const LanguageContext = React.createContext()

function App() {
    const [lang, setLang] = useState('es')
    const t = (key) => translations[lang]?.[key] || key

    return (
        <LanguageContext.Provider value={{ lang, setLang, t }}>
            <ChatView />
        </LanguageContext.Provider>
    )
}

export default App