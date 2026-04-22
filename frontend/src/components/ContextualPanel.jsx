import { useEffect, useState } from 'react'
import ChatPanel from './ChatPanel'
import { fetchContextualSubCategories } from '../services/api'
import './ContextualPanel.css'

const ContextualPanel = ({ showChat, setShowChat, selectedCategories = [] }) => {
  const [mode, setMode] = useState('panel')
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [isAnalyzed, setIsAnalyzed] = useState(false)
  const [subcategoryData, setSubcategoryData] = useState({})
  const [isLoadingSubcategories, setIsLoadingSubcategories] = useState(false)
  const [subcategoryError, setSubcategoryError] = useState('')

  useEffect(() => {
    if (mode !== 'panel') return

    if (!selectedCategories.length) {
      setSubcategoryData({})
      setSubcategoryError('')
      setIsLoadingSubcategories(false)
      return
    }

    let isCancelled = false

    async function loadSubcategories() {
      setIsLoadingSubcategories(true)
      setSubcategoryError('')

      try {
        const data = await fetchContextualSubCategories(selectedCategories)

        if (!isCancelled) {
          setSubcategoryData(data)
        }
      } catch (error) {
        if (!isCancelled) {
          setSubcategoryData({})
          setSubcategoryError('Failed to load subcategories.')
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingSubcategories(false)
        }
      }
    }

    loadSubcategories()

    return () => {
      isCancelled = true
    }
  }, [mode, selectedCategories])

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
    // <div className="relative flex h-full w-full">
    //   <div className="relative flex h-full w-full flex-col border-l border-white bg-[#bcd9d7] p-2 backdrop-blur-md">
    //     <button
    //       onClick={() => setShowChat(false)}
    //       className="absolute -left-8 top-1/2 -translate-y-1/2 z-50 bg-[#bcd9d7] border border-white rounded-l-md px-2 py-3 shadow-md hover:bg-[#a8c9c7] transition-all"
    //       aria-label="Close contextual panel"
    //     >
    //       {'>'}
    //     </button>

    //     <button
    //       onClick={() => setMode(mode === 'chat' ? 'panel' : 'chat')}
    //       className="absolute top-2 right-2 z-50 bg-black backdrop-blur-sm border border-gray-300 rounded-full p-1 shadow-md hover:scale-110 transition-all duration-200 flex items-center justify-center"
    //     >
    //       <img
    //         src={mode === 'chat' ? '/bar-chart.png' : '/message.png'}
    //         alt="toggle-mode"
    //         className="h-6 w-6 object-contain"
    //       />
    //     </button>

    //     {mode === 'chat' ? (
    //       <div className="min-h-0 flex-1 overflow-y-auto pt-12">
    //         <ChatPanel
    //           messages={messages}
    //           onSend={handleChat}
    //           isThinking={isThinking}
    //           isReady={isAnalyzed}
    //         />
    //       </div>
    //     ) : null}

    //     {mode === 'panel' && (
    //       <div className="min-h-0 flex-1 overflow-y-auto">
    //         <div className="mb-3 border-t border-white/30 pt-4">
    //           <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-700">
    //             Category Details
    //           </p>
    //           {/* <p className="mt-1 text-sm text-slate-800">
    //             {selectedCategories.length ? selectedCategories.join(', ') : 'No categories selected'}
    //           </p> */}
    //         </div>

    //         <div className="flex flex-col gap-3 pb-4">
    //           {isLoadingSubcategories && (
    //             <div className="rounded-lg bg-white/40 p-3 text-sm text-slate-700">
    //               Loading subcategories...
    //             </div>
    //           )}

    //           {!isLoadingSubcategories && subcategoryError && (
    //             <div className="rounded-lg bg-red-50/80 p-3 text-sm text-red-700">
    //               {subcategoryError}
    //             </div>
    //           )}

    //           {!isLoadingSubcategories && !subcategoryError && !selectedCategories.length && (
    //             <div className="rounded-lg bg-white/40 p-3 text-sm text-slate-700">
    //               Select one or more dashboard categories to view subcategory counts.
    //             </div>
    //           )}

    //           {!isLoadingSubcategories && !subcategoryError && selectedCategories.length > 0 && (
    //             selectedCategories.map((categoryKey) => {
    //               const items = Array.isArray(subcategoryData?.[categoryKey]) ? subcategoryData[categoryKey] : []

    //               return (
    //                 <div key={categoryKey} className="rounded-xl bg-white/50 p-3 shadow-sm">
    //                   <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-800">
    //                     {categoryKey}
    //                   </h3>

    //                   {items.length ? (
    //                     <div className="mt-2 flex flex-col gap-2">
    //                       {items.map((item) => (
    //                         <div
    //                           key={`${categoryKey}-${item.key}`}
    //                           className="flex items-center justify-between rounded-lg bg-white/70 px-3 py-2 text-sm text-slate-700"
    //                         >
    //                           <span>{item.key}</span>
    //                           <span className="font-semibold text-slate-900">{item.value}</span>
    //                         </div>
    //                       ))}
    //                     </div>
    //                   ) : (
    //                     <p className="mt-2 text-sm text-slate-600">
    //                       No subcategories found.
    //                     </p>
    //                   )}
    //                 </div>
    //               )
    //             })
    //           )}
    //         </div>
    //       </div>
    //     )}
    //   </div>
    // </div>
    <div className="relative flex h-full w-full">
      <div className="relative flex h-full w-full flex-col 
    border-l border-white/30 
    bg-gradient-to-b from-[#d7eeec] to-[#bcd9d7] 
    p-3 backdrop-blur-xl shadow-xl">

        {/* Toggle Mode Button */}
        <button
          onClick={() => setMode(mode === 'chat' ? 'panel' : 'chat')}
          className="absolute top-3 right-3 z-50 
      bg-white/60 backdrop-blur-md 
      border border-white/40 
      rounded-full p-2 shadow-md 
      hover:scale-110 hover:bg-white transition-all duration-200 
      flex items-center justify-center"
        >
          <img
            src={mode === 'chat' ? '/bar-chart.png' : '/message.png'}
            alt="toggle-mode"
            className="h-5 w-5 object-contain opacity-80"
          />
        </button>

        {/* CHAT MODE */}
        {mode === 'chat' && (
          <div className="min-h-0 flex-1 overflow-y-auto pr-1 custom-scroll">
            <ChatPanel
              messages={messages}
              onSend={handleChat}
              isThinking={isThinking}
              isReady={isAnalyzed}
            />
          </div>
        )}

        {/* PANEL MODE */}
        {mode === 'panel' && (
          <div className="min-h-0 flex-1 overflow-y-auto pr-1 custom-scroll">

            {/* Header */}
            <div className="mb-4 border-t border-white/30 pt-4 pr-12">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-700">
                Category Details
              </p>
            </div>

            <div className="flex flex-col gap-4 pb-4">

              {/* Loading */}
              {isLoadingSubcategories && (
                <div className="rounded-xl bg-white/60 p-3 text-sm text-slate-700 shadow-sm animate-pulse">
                  Loading subcategories...
                </div>
              )}

              {/* Error */}
              {!isLoadingSubcategories && subcategoryError && (
                <div className="rounded-xl bg-red-100/80 p-3 text-sm text-red-700 shadow-sm">
                  {subcategoryError}
                </div>
              )}

              {/* Empty */}
              {!isLoadingSubcategories && !subcategoryError && !selectedCategories.length && (
                <div className="rounded-xl bg-white/60 p-3 text-sm text-slate-700 shadow-sm">
                  Select categories to view subcategory insights.
                </div>
              )}

              {/* Data */}
              {!isLoadingSubcategories && !subcategoryError && selectedCategories.length > 0 &&
                selectedCategories.map((categoryKey) => {
                  const items = Array.isArray(subcategoryData?.[categoryKey])
                    ? subcategoryData[categoryKey]
                    : []

                  return (
                    <div
                      key={categoryKey}
                      className="rounded-2xl bg-white/60 backdrop-blur-md 
                  p-4 shadow-md border border-white/40"
                    >
                      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-800">
                        {categoryKey}
                      </h3>

                      {items.length ? (
                        <div className="mt-3 flex flex-col gap-2">
                          {items.map((item) => (
                            <div
                              key={`${categoryKey}-${item.key}`}
                              className="flex items-center justify-between 
                          rounded-lg bg-white/80 px-3 py-2 
                          text-sm text-slate-700 
                          shadow-sm hover:shadow-md 
                          transition-all"
                            >
                              <span className="truncate">{item.key}</span>
                              <span className="font-semibold text-slate-900">
                                {item.value}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-sm text-slate-600">
                          No subcategories found.
                        </p>
                      )}
                    </div>
                  )
                })
              }
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ContextualPanel
