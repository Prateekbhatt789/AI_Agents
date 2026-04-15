import { useState, useEffect } from 'react'
import { SearchIcon, SparklesIcon, TargetIcon } from './Icons'

export default function SearchBar({
    onSearch,
    onAnalyze,
    locationFound,
    isAnalyzing,
    locationName
}) {

    const [query, setQuery] = useState('')
    const [radius, setRadius] = useState(5)
    const radiusOptions = [1, 3, 5, 10]
    const [radiusIndex, setRadiusIndex] = useState(2) // default = 5 km

    useEffect(() => {
        if (locationName) {
            setQuery(locationName)
        }
    }, [locationName])

    useEffect(() => {
        setRadius(radiusOptions[radiusIndex])
    }, [radiusIndex])

    function handleSearch() {
        if (!query.trim()) return
        onSearch(query.trim(), radius)
    }

    return (
        <div className="group rounded-xl  bg-white/72 p-2 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
            <div className='ml-3 mb-2'>
                <div className="mb-1 flex  items-center gap-2">
                    <div className="flex h-3 w-3 min-h-[1.5rem] min-w-[1.5rem] items-center justify-center rounded-full bg-slate-900 text-white shadow-lg shadow-slate-900/15">
                        <TargetIcon className="h-5 w-5" />
                    </div>
                    <div>
                        <h3 className="font-bold uppercase text-slate-900">
                            Search Location
                        </h3>
                    </div>
                </div>
                <p className="text-xs text-slate-500 opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                    Pick a place, radius, and start the analysis.
                </p>
            </div>

            <div className="mb-3 flex w-full items-center rounded-2xl border border-slate-200 bg-white/80  shadow-sm backdrop-blur-sm focus-within:ring-2 focus-within:ring-cyan-400">
                <input
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    placeholder="Search location or click on map..."
                    className="flex-1 bg-transparent px-2 py-2.5 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                />
                <button
                    className="cursor-pointer"
                    onClick={handleSearch}
                >
                    <SearchIcon className="h-7 w-7 mr-1" />
                </button>
            </div>

            <div className="px-2 py-2">
                {/* Header */}
                <div className="flex items-center justify-between mb-5">
                    <div>
                        <h3 className="text-base font-medium text-slate-900">
                            Search radius
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 m-0">
                            Adjust your search area
                        </p>
                    </div>
                    <div className="text-right text-[#0f766e]">
                        <div className="text-2xl font-medium ">
                            <span>{radiusOptions[radiusIndex]}</span>
                            <span className="text-sm ml-1">
                                km
                            </span>
                        </div>
                    </div>
                </div>

                {/* Slider Container */}
                <div className="relative">
                    <input
                        type="range"
                        min={0}
                        max={radiusOptions.length - 1}
                        step={1}
                        value={radiusIndex}
                        onChange={(e) => setRadiusIndex(Number(e.target.value))}
                        className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full outline-none appearance-none cursor-pointer
        [&::-webkit-slider-thumb]:appearance-none
        [&::-webkit-slider-thumb]:w-5
        [&::-webkit-slider-thumb]:h-5
        [&::-webkit-slider-thumb]:rounded-full
        [&::-webkit-slider-thumb]:bg-gradient-to-br
        [&::-webkit-slider-thumb]:from-blue-500
        [&::-webkit-slider-thumb]:to-cyan-500
        [&::-webkit-slider-thumb]:cursor-pointer
        [&::-webkit-slider-thumb]:shadow-lg
        [&::-webkit-slider-thumb]:shadow-blue-400/40
        [&::-webkit-slider-thumb]:transition-transform
        [&::-webkit-slider-thumb]:duration-200
        hover:[&::-webkit-slider-thumb]:scale-125
        [&::-moz-range-thumb]:w-5
        [&::-moz-range-thumb]:h-5
        [&::-moz-range-thumb]:rounded-full
        [&::-moz-range-thumb]:bg-gradient-to-br
        [&::-moz-range-thumb]:from-blue-500
        [&::-moz-range-thumb]:to-cyan-500
        [&::-moz-range-thumb]:cursor-pointer
        [&::-moz-range-thumb]:border-0
        [&::-moz-range-thumb]:shadow-lg
        [&::-moz-range-thumb]:shadow-blue-400/40
        [&::-moz-range-thumb]:transition-transform
        [&::-moz-range-thumb]:duration-200
        hover:[&::-moz-range-thumb]:scale-125
        [&::-moz-range-track]:bg-transparent
        [&::-moz-range-track]:border-0
      "
                    />

                    {/* Tick marks and labels */}
                    <div className="flex justify-between mt-3 px-0.5 text-xs text-slate-400 dark:text-slate-500">
                        <span>1</span>
                        <span>10</span>
                    </div>
                </div>

            </div>
            <button
                onClick={onAnalyze}
                disabled={!locationFound || isAnalyzing}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/40 transition-all duration-200 hover:shadow-xl hover:shadow-blue-600/50 hover:scale-105 active:scale-95 disabled:cursor-not-allowed disabled:from-[#87aacf] disabled:to-[#3d88d8] disabled:shadow-none disabled:hover:scale-100 disabled:opacity-60"
            >
                <SparklesIcon className="h-5 w-5" />
                <span>
                    {isAnalyzing ? (
                        <>
                            <span className="inline-block animate-spin mr-1">⚡</span>
                            Analyzing...
                        </>
                    ) : (
                        'Analyze Selected Area'
                    )}
                </span>
            </button>
        </div>
    )
}
