import { useState, useRef, useEffect } from 'react'
import {
    BotIcon,
    BusIcon,
    ChartIcon,
    HospitalIcon,
    SchoolIcon,
    SendIcon
} from './Icons'

const QUICK_QUESTIONS = [
    { label: 'Human Hospitals', text: 'Is this a good location to open a Hospital for Human?', icon: HospitalIcon },
    { label: 'Transport', text: 'How is the public transport connectivity?', icon: BusIcon },
    { label: 'For school?', text: 'Is this a good location to open a School?', icon: SchoolIcon },
    { label: 'Summary', text: 'Give me a complete site analysis summary.', icon: ChartIcon },
]

export default function ChatPanel({ messages, onSend, isThinking, isReady }) {

    const [input, setInput] = useState('')
    const bottomRef = useRef(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, isThinking])

    function handleSend() {
        if (!input.trim() || !isReady) return
        onSend(input.trim())
        setInput('')
    }

    return (
        <div className="flex h-full flex-col gap-3 rounded-2xl border border-slate-200/50 bg-white p-4 shadow-[0_2px_8px_rgba(15,23,42,0.06)]">
            {/* Header */}
            <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                <div className="flex h-8  w-8 items-center justify-center rounded-full bg-gradient-to-br from-[#00a1ef] to-[#11b3ff] text-white">
                    <BotIcon className="h-7 w-7" />
                </div>
                <div>
                    <h2 className="text-lg font-bold font-500 text-slate-900">
                        AI Location Analyst
                    </h2>
                   
                </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto px-1">
                {messages.length === 0 ? (
                    <div className="flex flex-1 flex-col items-center justify-center text-center gap-2">
                        <div className="text-xs text-slate-500 max-w-[80%]">
                            Ask planning questions once the site is analyzed.
                        </div>
                    </div>
                ) : (
                    messages.map((msg, i) => (
                        <div
                            key={i}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[85%] rounded-xl px-4 py-2.5 text-xs leading-relaxed ${msg.role === 'user'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-slate-100 text-slate-900'
                                    }`}
                            >
                                {msg.text}
                            </div>
                        </div>
                    ))
                )}

                {isThinking && (
                    <div className="flex justify-start">
                        <div className="bg-slate-100 text-slate-600 rounded-xl px-4 py-2.5 text-xs">
                            <div className="flex items-center gap-2">
                                <div className="flex gap-1">
                                    <span className="inline-block w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                    <span className="inline-block w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                    <span className="inline-block w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                </div>
                                Analyzing...
                            </div>
                        </div>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Quick Actions */}
            {messages.length === 0 && !isThinking && (
                <div className="flex flex-wrap gap-2 pb-2">
                    {QUICK_QUESTIONS.map(({ label, text, icon: Icon }) => (
                        <button
                            key={label}
                            onClick={() => isReady && onSend(text)}
                            disabled={!isReady}
                            className="flex items-center gap-1.5 rounded-lg border border-slate-200 hover:border-blue-300 bg-slate-50 hover:bg-blue-50 px-3 py-2 text-xs text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            <Icon className="h-3.5 w-3.5 flex-shrink-0" />
                            <span>{label}</span>
                        </button>
                    ))}
                </div>
            )}

            {/* Input Area */}
            <div className="flex gap-2 pt-2 border-t border-slate-100">
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                    placeholder={isReady ? 'Ask about a location...' : 'Loading...'}
                    disabled={!isReady}
                    className="flex-1 rounded-lg border border-slate-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 bg-white px-3.5 py-2.5 text-xs text-slate-900 placeholder-slate-400 outline-none transition-all disabled:opacity-60 disabled:bg-slate-50"
                />
                <button
                    onClick={handleSend}
                    disabled={!isReady || !input.trim()}
                    className="flex items-center justify-center rounded-lg bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 text-xs font-500 transition-colors disabled:bg-slate-300 disabled:cursor-not-allowed"
                >
                    <SendIcon className="h-4 w-4" />
                </button>
            </div>
        </div>
    )
}
