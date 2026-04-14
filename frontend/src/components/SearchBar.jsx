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

    useEffect(() => {
        if (locationName) {
            setQuery(locationName)
        }
    }, [locationName])

    function handleSearch() {
        if (!query.trim()) return
        onSearch(query.trim(), radius)
    }

    return (
        <div className="rounded-3xl border border-white/55 bg-white/72 p-5 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
            <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-lg shadow-slate-900/15">
                    <TargetIcon className="h-5 w-5" />
                </div>
                <div>
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-900">
                        Search Location
                    </h3>
                    <p className="text-xs text-slate-500">
                        Pick a place, radius, and start the analysis.
                    </p>
                </div>
            </div>

            <div className="mb-3 flex w-full items-center gap-2">
                <input
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    placeholder="e.g. Saket or click map"
                    className="min-w-0 w-full rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
                />

                <button
                    onClick={handleSearch}
                    className="flex shrink-0 items-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
                >
                    <SearchIcon className="h-4 w-4" />
                    Search
                </button>
            </div>

            <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-500">Radius</span>

                <select
                    value={radius}
                    onChange={e => setRadius(Number(e.target.value))}
                    className="rounded-2xl border border-slate-200 bg-white/90 px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
                >
                    <option value={1}>1 km</option>
                    <option value={3}>3 km</option>
                    <option value={5}>5 km</option>
                    <option value={10}>10 km</option>
                </select>

                <button
                    onClick={onAnalyze}
                    disabled={!locationFound || isAnalyzing}
                    className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-linear-to-r from-cyan-500 to-teal-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition hover:from-cyan-400 hover:to-teal-400 disabled:cursor-not-allowed disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none"
                >
                    <SparklesIcon className="h-4 w-4" />
                    {isAnalyzing ? 'Analyzing...' : 'Analyze this Area'}
                </button>
            </div>
        </div>
    )
}
