import { useState } from "react";
import SearchBar from './SearchBar'
import Dashboard from "./Dashboard";
import { DownloadIcon } from './Icons'

export default function SidePanel() {
    const [lat, setLat] = useState(null)
    const [lon, setLon] = useState(null)
    const [locationName, setLocationName] = useState('')
    const [summary, setSummary] = useState({})
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [isAnalyzed, setIsAnalyzed] = useState(false)

    async function handleSearch(query, radius) {
        setStatus('Searching...')
        setRadiusKm(radius)
        try {
            const data = await searchLocation(query)
            setLat(data.lat)
            setLon(data.lon)
            setLocationName(data.place_name)
            setPoiData(null)
            setSummary({})
            setIsAnalyzed(false)
            setSuggestions([])
            setSessionId(null)
            setStatus(`Found: ${data.place_name}`)
        } catch (err) {
            setStatus('Not found')
            alert(err.message)
        }
    }

    async function handleAnalyze() {
        if (!lat || !lon) return
        setIsAnalyzing(true)

        try {
            setStatus('Fetching data from OpenStreetMap...')
            const pois = await fetchPOIs(lat, lon, radiusKm)
            setPoiData(pois)
            setSummary(pois.summary)

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
            setStatus(`Done - ${locationName}`)
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
            className="flex w-80 shrink-0 flex-col gap-2 overflow-y-auto border-r border-white/40 bg-[#0f766e] p-2 backdrop-blur-md"
        >
            <SearchBar
                onSearch={handleSearch}
                onAnalyze={handleAnalyze}
                locationFound={!!lat}
                isAnalyzing={isAnalyzing}
                locationName={locationName}
            />
            <Dashboard
                locationName={locationName}
                summary={summary}
                onDownload={handleDownload}
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