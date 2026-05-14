import { useEffect, useState } from 'react'
import ChatPanel from './ChatPanel'
import './ContextualPanel.css'

const ContextualPanel = ({
  showChat,
  setShowChat,
  mode = 'panel',
  onModeChange,
  selectedCategories = [],
  messages = [],
  onSend,
  isChatSearching = false,
  isReady = false,
  poiData = null,
  selectedSubcategories = {},
  setSelectedSubcategories,
}) => {
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

    function normalizeKey(value) {
      return String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[_\s-]+/g, '')
    }

    async function loadSubcategories() {
      setIsLoadingSubcategories(true)
      setSubcategoryError('')

      try {
        const pois = poiData?.pois || {}
        const poiKeys = Object.keys(pois)
        const normalizedPoiMap = Object.fromEntries(
          poiKeys.map((key) => [normalizeKey(key), key])
        )
        const data = {}

        selectedCategories.forEach((categoryKey) => {
          const normalizedCategory = normalizeKey(categoryKey)
          const matchedPoiKey = normalizedPoiMap[normalizedCategory]
          const items = matchedPoiKey && Array.isArray(pois[matchedPoiKey])
            ? pois[matchedPoiKey]
            : []
          const counts = items.reduce((acc, poi) => {
            const subCategory = poi.sub_category || 'Unknown'
            acc[subCategory] = (acc[subCategory] || 0) + 1
            return acc
          }, {})

          data[categoryKey] = Object.entries(counts)
            .map(([key, value]) => ({ key, value }))
            .sort((a, b) => b.value - a.value)
        })

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
  }, [mode, selectedCategories, poiData])

  function toggleSubcategory(categoryKey, subcategoryKey) {
    setSelectedSubcategories?.((previousSelections) => {
      const currentSelection = previousSelections[categoryKey] || []
      const nextCategorySelection = currentSelection.includes(subcategoryKey)
        ? currentSelection.filter((key) => key !== subcategoryKey)
        : [...currentSelection, subcategoryKey]
      const nextSelections = { ...previousSelections }

      if (nextCategorySelection.length > 0) {
        nextSelections[categoryKey] = nextCategorySelection
      } else {
        delete nextSelections[categoryKey]
      }

      return nextSelections
    })
  }

  function clearSubcategorySelection(categoryKey) {
    setSelectedSubcategories?.((previousSelections) => {
      const nextSelections = { ...previousSelections }
      delete nextSelections[categoryKey]
      return nextSelections
    })
  }

  if (!showChat) return null

  return (
    <div className="relative flex h-full w-full">
      <div className="relative flex h-full w-full flex-col 
    border-l border-white/30 
    bg-gradient-to-b from-[#d7eeec] to-[#bcd9d7] 
    p-3 backdrop-blur-xl shadow-xl">

        {/* Toggle Mode Button */}
        <button
          onClick={() => onModeChange?.(mode === 'chat' ? 'panel' : 'chat')}
          title={mode === 'chat' ? 'Switch to Panel View' : 'Chat With Jarvis'}
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
              onSend={onSend}
              isThinking={isChatSearching}
              isReady={isReady}
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
                <div className="rounded-xl bg-white/60 p-3 text-st text-slate-700 shadow-sm animate-pulse">
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
                selectedCategories
                  .map((categoryKey) => {
                    const items = Array.isArray(subcategoryData?.[categoryKey])
                      ? subcategoryData[categoryKey]
                      : []
                    return { categoryKey, items }
                  })
                  .filter(({ items }) => items.length > 0)
                  .map(({ categoryKey, items }) => {
                    const selectedItems = selectedSubcategories[categoryKey] || []

                  return (
                    <div
                      key={categoryKey}
                      className="rounded-2xl bg-white/60 backdrop-blur-md 
                  p-4 shadow-md border border-white/40"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="truncate text-sm font-semibold uppercase tracking-wide text-slate-800">
                          {categoryKey}
                        </h3>
                        {selectedItems.length > 0 && (
                          <button
                            type="button"
                            onClick={() => clearSubcategorySelection(categoryKey)}
                            className="shrink-0 rounded-full border border-slate-200 bg-white/80 px-2 py-1 text-[11px] font-semibold text-slate-600 transition hover:border-cyan-400 hover:text-cyan-700"
                          >
                            Clear
                          </button>
                        )}
                      </div>

                      <div className="mt-3 flex flex-col gap-2">
                        {items.map((item) => {
                          const isSelected = selectedItems.includes(item.key)

                          return (
                            <button
                              key={`${categoryKey}-${item.key}`}
                              type="button"
                              onClick={() => toggleSubcategory(categoryKey, item.key)}
                              className={`flex items-center justify-between rounded-lg border px-3 py-2 text-left text-sm shadow-sm transition-all hover:shadow-md
                                ${isSelected
                                  ? 'border-cyan-500 bg-cyan-600 text-white'
                                  : 'border-white/70 bg-white/80 text-slate-700 hover:border-cyan-300'
                                }`}
                            >
                              <span className="min-w-0 truncate">{item.key}</span>
                              <span className={`ml-3 shrink-0 font-semibold ${isSelected ? 'text-white' : 'text-slate-900'}`}>
                                {item.value}
                              </span>
                            </button>
                          )
                        })}
                      </div>
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
