import { useState } from 'react'
import ChatPanel from './ChatPanel'

const ContextualPanel = ({ showChat, setShowChat }) => {
  const [mode, setMode] = useState('panel')
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [isAnalyzed, setIsAnalyzed] = useState(false)
  const [categories] = useState([
    { name: 'Shops', emoji: 'ðŸª' },
    { name: 'Food', emoji: 'ðŸ½ï¸' },
    { name: 'Health', emoji: 'ðŸ¥' },
  ])

  async function handleChat(message) {
    setMessages((prev) => [...prev, { role: 'user', text: message }])
    setIsThinking(true)

    try {
      const response = 'Demo response from AI'

      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: response }
      ])
    } catch (err) {
      console.error(err)
      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: 'Error. Please try again.' }
      ])
    } finally {
      setIsThinking(false)
    }
  }

  if (!showChat) return null

  return (
    <div className="relative h-full flex">
      <div className="relative w-80 border-l border-white bg-[#bcd9d7] p-2 backdrop-blur-md flex flex-col h-full">
        <button
          onClick={() => setShowChat(false)}
          className="absolute -left-8 top-1/2 -translate-y-1/2 z-50 bg-[#bcd9d7] border border-white rounded-l-md px-2 py-3 shadow-md hover:bg-[#a8c9c7] transition-all"
          aria-label="Close contextual panel"
        >
          ▶
        </button>

        <button
          onClick={() => setMode(mode === 'chat' ? 'panel' : 'chat')}
          className="absolute top-2 right-2 z-50 bg-black backdrop-blur-sm border border-gray-300 rounded-full p-1 shadow-md hover:scale-110 transition-all duration-200 flex items-center justify-center"
        >
          <img
            src={mode === 'chat' ? '/bar-chart.png' : '/message.png'}
            alt="toggle-mode"
            className="h-6 w-6 object-contain"
          />
        </button>

        <div className="flex-1 overflow-y-auto">
          {mode === 'chat' ? (
            <ChatPanel
              messages={messages}
              onSend={handleChat}
              isThinking={isThinking}
              isReady={isAnalyzed}
            />
          ) : null}
        </div>

        {mode === 'panel' && (
          <div className="flex flex-col gap-3 mt-auto pt-4 border-t border-white/30">
            {categories.map((category) => (
              <button
                key={category.name}
                className="text-left hover:bg-white/50 p-2 rounded transition-colors"
              >
                {category.emoji} {category.name}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ContextualPanel
