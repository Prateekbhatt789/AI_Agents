import { useState } from 'react'
import SearchBar from './components/SearchBar'
import Dashboard from './components/Dashboard'
import MapViewer from './components/MapViewer'
import ChatPanel from './components/ChatPanel'
import { GlobeIcon, LoaderIcon, PinIcon } from './components/Icons'
import {
  searchLocation,
  fetchPOIs,
  analyzeLocation,
  chatWithAgent,
  exportPDF,
  reverseGeocode
} from './services/api'

function AnalyzeLoader({ status }) {
  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      background: 'rgba(236, 253, 245, 0.42)',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '20px',
      backdropFilter: 'blur(10px)',
    }}>

      <div style={{
        width: '64px',
        height: '64px',
        borderRadius: '24px',
        background: 'linear-gradient(135deg, #0f172a, #0891b2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 24px 60px rgba(15,23,42,0.22)',
      }}>
        <LoaderIcon className="h-8 w-8 animate-spin text-white" />
      </div>

      <div style={{ textAlign: 'center' }}>
        <p style={{
          color: '#0f172a',
          fontSize: '15px',
          fontWeight: '600',
          margin: '0 0 6px',
        }}>
          Analyzing area
        </p>
        <p style={{
          color: '#475569',
          fontSize: '13px',
          margin: 0,
        }}>
          {status}
        </p>
      </div>

      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: '#0891b2',
            opacity: 1 - i * 0.3,
            animation: `pulse 1.2s ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>

      <style>{`
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.2; } }
      `}</style>
    </div>
  )
}

export default function App() {

  const [lat, setLat] = useState(null)
  const [lon, setLon] = useState(null)
  const [radiusKm, setRadiusKm] = useState(5)
  const [locationName, setLocationName] = useState('')
  const [poiData, setPoiData] = useState(null)
  const [summary, setSummary] = useState({})
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isAnalyzed, setIsAnalyzed] = useState(false)
  const [status, setStatus] = useState('Ready')
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Search a location or click on the map, then run an analysis.' }
  ])
  const [isThinking, setIsThinking] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [showAdmin, setShowAdmin] = useState(false)

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

  async function handleMapClick(clickLat, clickLon) {
    setStatus('Getting location name...')
    try {
      const data = await reverseGeocode(clickLat, clickLon)
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
      setStatus('Could not get location name')
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

  async function handleChat(message) {
    addMessage('user', message)
    setIsThinking(true)
    setSuggestions([])

    try {
      const data = await chatWithAgent(message, sessionId)

      console.log('DEBUG chat response:', data)
      console.log('DEBUG suggestions:', data.suggestions)

      addMessage('ai', data.response)

      if (data.suggestions && data.suggestions.length > 0) {
        setSuggestions(data.suggestions)
        console.log(`DEBUG ${data.suggestions.length} pins set`)
      }

    } catch (err) {
      console.error(err)
      addMessage('ai', 'Error. Please try again.')
    } finally {
      setIsThinking(false)
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

  function addMessage(role, text) {
    setMessages(prev => [...prev, { role, text }])
  }

  const statusTone = status === 'Ready'
    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
    : status.startsWith('Failed')
      ? 'bg-rose-50 text-rose-700 border-rose-200'
      : 'bg-cyan-50 text-cyan-700 border-cyan-200'

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.2),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(20,184,166,0.18),_transparent_24%),linear-gradient(180deg,_#f8fafc_0%,_#e2e8f0_100%)] text-slate-900">
      {/* <nav className="flex h-20 items-center justify-between border-b border-white/50 [#CFECF3] px-6 backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <div className="relative">
            <img
              className="h-12 w-12 rounded-2xl object-contain shadow-lg shadow-slate-900/10 ring-1 ring-white/70"
              src="/nav_logo.png"
              alt="Logo"
            />
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-cyan-500 text-white">
              <PinIcon className="h-2.5 w-2.5" />
            </span>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-700">
              Spatial Intelligence
            </p>
            <span className="text-xl font-semibold tracking-[0.04em] text-slate-900">
              GIS AI Agent
            </span>
          </div>
        </div>

        <span className={`inline-flex items-center gap-3 rounded-full border px-4 py-2 text-xs font-semibold shadow-sm ${statusTone}`}>
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-30" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-current" />
          </span>
          {status}
        </span>
      </nav> */}
      <nav className="flex h-20 items-center justify-between bg-[#F9F8F6] border-b border-cyan-200 px-6 shadow-sm">

        {/* Left Section */}
        <div className="flex items-center gap-4">

          <div className="relative">
            <img
              className="h-20 w-20 object-contain "
              src="/image.png"
              alt="Logo"
            />
            {/* <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-cyan-600 text-white">
              <PinIcon className="h-2.5 w-2.5" />
            </span> */}
          </div>

          <div>
            <p
              className="m-0 mb-[5px] text-[28px] leading-none font-montserrat font-bold uppercase "
            >
              <span className="text-[#011649]">Geo-Spatial</span>{" "}
              <span className="text-[#64ae09]">Intelligence</span>
            </p>
            <span className="block text-xl leading-none font-bold tracking-wide text-[#019ee1]">
              Locate : Analyze : Act
            </span>
          </div>

        </div>

      <div className='flex items-center gap-3'>
        {/* Status */}
        <span className={`inline-flex items-center gap-3 rounded-full border border-cyan-300 bg-white px-4 py-2 text-xs font-semibold shadow-sm ${statusTone}`}>

          <span className="relative flex h-2.5 w-2.5 text-green-500">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-30" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-current" />
          </span>

          {status}
        </span>
        <div className="relative">
          <img
            className="h-10 w-10 cursor-pointer rounded-full object-cover"
            src="/user.png"
            alt="User"
            onClick={() => setShowAdmin(prev => !prev)}
          />
          {showAdmin && (
            <div className="absolute z-10 right-0 top-full rounded-md border border-cyan-200 bg-white px-3 py-1 text-sm font-semibold text-slate-700 shadow-md">
              admin
            </div>
          )}
        </div>
        </div>

      </nav>
      <div className="flex flex-1 overflow-hidden">
        <div className="flex w-80 shrink-0 flex-col gap-4 overflow-y-auto border-r border-white/40 bg-white/25 p-4 backdrop-blur-md">
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

        <div className="relative flex-1">
          {!lat && !isAnalyzing && (
            <div className="pointer-events-none absolute inset-0 z-10 flex flex-col items-center justify-center text-slate-500">
              <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-[2rem] border border-white/70 bg-white/75 text-cyan-700 shadow-2xl shadow-slate-900/10 backdrop-blur-xl">
                <GlobeIcon className="h-9 w-9" />
              </div>
              <p className="text-sm font-medium">Search or click on the map to select a location</p>
            </div>
          )}

          {isAnalyzing && (
            <AnalyzeLoader status={status} />
          )}

          <MapViewer
            lat={lat}
            lon={lon}
            radiusKm={radiusKm}
            poiData={poiData}
            suggestions={suggestions}
            onMapClick={handleMapClick}
            isAnalyzing={isAnalyzing}
            isAnalyzed={isAnalyzed}
          />
        </div>

        <div className="w-80 shrink-0 border-l border-white/40 bg-white/25 p-4 backdrop-blur-md">
          <ChatPanel
            messages={messages}
            onSend={handleChat}
            isThinking={isThinking}
            isReady={isAnalyzed}
          />
        </div>

      </div>
    </div>
  )
}
