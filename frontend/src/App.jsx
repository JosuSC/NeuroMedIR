import React, { useState } from 'react'
import { ChatView } from './components/chat/ChatView'
import { AssessmentView } from './components/assessment/AssessmentView'

function App() {
    // Simple router for now
    const [currentView, setCurrentView] = useState('chat')

    return (
        <div>
            {/* Test Buttons to switch views */}
            <div className="fixed top-2 left-1/2 -translate-x-1/2 z-[100] flex gap-2 bg-white/80 backdrop-blur-md p-2 rounded-full border border-outline-variant shadow-sm">
                <button
                    onClick={() => setCurrentView('chat')}
                    className={`px-3 py-1 rounded-full text-xs font-bold ${currentView === 'chat' ? 'bg-primary text-white' : 'bg-surface-container text-on-surface'}`}
                >
                    Consult (Chat RAG)
                </button>
                <button
                    onClick={() => setCurrentView('assessment')}
                    className={`px-3 py-1 rounded-full text-xs font-bold ${currentView === 'assessment' ? 'bg-primary text-white' : 'bg-surface-container text-on-surface'}`}
                >
                    Assessment
                </button>
            </div>

            {currentView === 'chat' && <ChatView />}
            {currentView === 'assessment' && <AssessmentView />}
        </div>
    )
}

export default App