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
        <div className="flex h-full flex-col gap-4 rounded-3xl border border-white/55 bg-white/72 p-5 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
            <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-lg shadow-slate-900/15">
                    <BotIcon className="h-5 w-5" />
                </div>
                <div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-900">
                        AI Location Analyst
                    </h3>
                    <p className="text-xs text-slate-500">
                        Ask planning questions once the site is analyzed.
                    </p>
                </div>
            </div>

            <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
                {messages.map((msg, i) => (
                    <div
                        key={i}
                        className={`max-w-[95%] rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-sm ${msg.role === 'user'
                            ? 'self-end border border-cyan-200 bg-cyan-50 text-slate-700'
                            : 'self-start border border-slate-200 bg-white text-slate-700'
                            }`}
                    >
                        {msg.text}
                    </div>
                ))}

                {isThinking && (
                    <div className="self-start rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs italic text-slate-500 shadow-sm">
                        Thinking...
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            <div className="flex flex-wrap gap-1">
                {QUICK_QUESTIONS.map(({ label, text, icon: Icon }) => (
                    <button
                        key={label}
                        onClick={() => isReady && onSend(text)}
                        disabled={!isReady}
                        className="flex items-center gap-2 rounded-full border border-slate-200 bg-white/90 px-3 py-2 text-[10px] text-slate-600 transition hover:border-cyan-300 hover:bg-cyan-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                        <Icon className="h-3.5 w-3.5" />
                        {label}
                    </button>
                ))}
            </div>

            <div className="flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSend()}
                    placeholder={isReady
                        ? 'Ask about this location...'
                        : 'Analyze a location first...'
                    }
                    disabled={!isReady}
                    className="flex-1 rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-xs text-slate-700 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100 disabled:opacity-50"
                />
                <button
                    onClick={handleSend}
                    disabled={!isReady || !input.trim()}
                    className="flex items-center gap-2 rounded-2xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                    <SendIcon className="h-4 w-4" />
                    Send
                </button>
            </div>
        </div>
    )
}
