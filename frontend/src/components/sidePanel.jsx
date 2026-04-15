import { useState } from "react";
import SearchBar from './SearchBar'
import Dashboard from "./Dashboard";

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
        className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-r border-white/40 bg-[#0f766e] p-2 backdrop-blur-md"
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
        </div>
    )
}