import { useState } from "react";
import SearchBar from './SearchBar'
import Dashboard from "./Dashboard";
import { DownloadIcon } from './Icons'
import './sidePanel.css'
import {
    searchLocation,
    fetchPOIs,
    analyzeLocation,
    exportPDF
} from '../services/api'
import { isWithinDelhiBoundary } from '../utils/delhiBoundary'

export default function SidePanel({ lat,
    lon,
    radiusKm,
    locationName,
    summary,
    isAnalyzing,
    isAnalyzed,
    onSearch,
    onAnalyze,
    onDownload,
    setIsAnalyzing,
    setIsAnalyzed,
    setSummary,
    setLat,
    setLon,
    setLocationName,
    setPoiData,
    setStatus,
    setSuggestions,
    setSessionId, setRadiusKm,
    addMessage,
    openContextualPanel,
    setSelectedCategories,
    // to show grid over map
    setGridData, setShowGrid, showGrid }
) {
    // const [lat, setLat] = useState(null)
    // const [lon, setLon] = useState(null)
    // const [locationName, setLocationName] = useState('')
    // const [summary, setSummary] = useState({})
    // const [isAnalyzing, setIsAnalyzing] = useState(false)
    // const [isAnalyzed, setIsAnalyzed] = useState(false)

    async function handleSearch(query, radius) {
        setStatus('Searching...')
        setRadiusKm(radius)

        try {
            const data = await searchLocation(query)

            const latitude = data?.lat
            const longitude = data?.lon

            const isInside = isWithinDelhiBoundary(latitude, longitude)

            if (!isInside) {
                setStatus('Location is outside allowed boundary ')
                return
            }

            // If inside → proceed normally
            setLat(latitude)
            setLon(longitude)
            setLocationName(data.place_name)
            setPoiData(null)
            setSummary({})
            setIsAnalyzed(false)
            setSuggestions([])
            setSessionId(null)
            // setShowChat(false)

            setStatus(`Found: ${data.place_name} Inside boundary`)
        } catch (err) {
            setStatus('Location not found')
        }
    }

    async function handleAnalyze() {
        if (!lat || !lon) return
        setIsAnalyzing(true)

        try {
            setStatus('Fetching data ...')
            const pois = await fetchPOIs(lat, lon, radiusKm)
            setPoiData(pois)
            setSummary(pois.summary)
            setGridData(pois.grids ?? [])   // to show grid over map

            setStatus('Storing data and building spatial grid...')
            const analyzeResult = await analyzeLocation(
                locationName, lat, lon, radiusKm, pois
            )

            if (analyzeResult?.session_id) {
                setSessionId(analyzeResult.session_id)
                console.log('Session ID:', analyzeResult.session_id)
            }

            setIsAnalyzed(true)
            setSuggestions([])
            openContextualPanel?.('chat')
            setStatus(`Done`)
            addMessage('ai', `Analysis complete for ${locationName}. Spatial grid ready. Ask me anything.`)

        } catch (err) {
            setStatus('Failed')
            console.error(err)
            alert(err.message || 'Failed. Try a smaller radius.')
        } finally {
            setIsAnalyzing(false)
        }
    }

    async function handleDownload() {
        if (!isAnalyzed) return
        try {
            const blob = await exportPDF(locationName, lat, lon, radiusKm, summary)
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'site_report.pdf'
            a.click()
            URL.revokeObjectURL(url)
        } catch {
            alert('PDF failed.')
        }
    }


    return (
        <div
            className="side-panel-scrollbar flex w-80 shrink-0 flex-col gap-2 overflow-y-auto border-r border-white/40 bg-[#0f766e] p-2 backdrop-blur-md"
        >
            <SearchBar
                onSearch={handleSearch}
                onAnalyze={handleAnalyze}
                onOpenContextualPanel={openContextualPanel}
                locationFound={!!lat}
                isAnalyzing={isAnalyzing}
                locationName={locationName}
                setRadiusKm={setRadiusKm}
                // to grids over the map
                showGrid={showGrid}
                setShowGrid={setShowGrid}
            />
            <Dashboard
                locationName={locationName}
                summary={summary}
                onDownload={handleDownload}
                onItemClick={() => openContextualPanel?.('panel')}
                onSelectionChange={setSelectedCategories}
            />
            <div className="flex w-full items-center justify-center gap-1 rounded-2xl  bg-white/72  py-2 text-sm font-semibold text-slate-900 transition hover:bg-[#14b8a6] hover:text-white hover:border hover:border-white">
                <button
                    onClick={handleDownload}
                    className="flex gap-2 items-center justify-center ">
                    {/* Icon with black background */}
                    <span className="flex items-center justify-center h-5 w-5 rounded-full bg-black text-white">
                        <DownloadIcon className="h-4 w-4" />
                    </span>
                    <div className="text-xl">
                        Download Report
                    </div>
                </button>
            </div>
        </div>
    )
}
