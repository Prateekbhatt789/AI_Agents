import { useState } from 'react'
import SearchBar from './components/SearchBar'
import Dashboard from './components/Dashboard'
import MapViewer from './components/MapViewer'
import ChatPanel from './components/ChatPanel'
import SidePanel from './components/sidePanel'
import { GlobeIcon, LoaderIcon, PinIcon } from './components/Icons'
import {
  searchLocation,
  fetchPOIs,
  analyzeLocation,
  chatWithAgent,
  exportPDF,
  reverseGeocode
} from './services/api'
import ContextualPanel from './components/ContextualPanel'
import { isWithinDelhiBoundary } from './utils/delhiBoundary'

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
  const [radiusKm, setRadiusKm] = useState(1)
  const [poiData, setPoiData] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isAnalyzed, setIsAnalyzed] = useState(false)
  const [status, setStatus] = useState('Ready')
  const [locationName, setLocationName] = useState('')
  const [summary, setSummary] = useState({})
  const [messages, setMessages] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [showAdmin, setShowAdmin] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState([])
  
  async function handleSearch(query, radius) {
    setStatus('Searching...')
    setRadiusKm(radius)
    
    try {
      const data = await searchLocation(query)

      let lat = data?.lat
      let lon = data?.lon

      const isInside = isWithinDelhiBoundary(lat, lon)

      if (!isInside) {
        setStatus('Location is outside allowed boundary ')
        return
      }

      // If inside → proceed normally
      setLat(lat)
      setLon(lon)
      setLocationName(data.place_name)
      setPoiData(null)
      setSummary({})
      setIsAnalyzed(false)
      setSuggestions([])
      setSessionId(null)
      setShowChat(false)
      setSelectedCategories([])

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


  function addMessage(role, text) {
    setMessages(prev => [...prev, { role, text }])
  }

  async function handleMapClick(clickLat, clickLon) {
    if (!isWithinDelhiBoundary(clickLat, clickLon)) {
      setStatus('Selected location is outside allowed boundary')
      return
    }

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
      setShowChat(false)
      setSelectedCategories([])
      setStatus(`Found: ${data.place_name}`)
    } catch (err) {
      setStatus('Could not get location name')
    }
  }


  const statusTone = status === 'Ready'
    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
    : status.startsWith('Failed')
      ? 'bg-rose-50 text-rose-700 border-rose-200'
      : 'bg-cyan-50 text-cyan-700 border-cyan-200'

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.2),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(20,184,166,0.18),_transparent_24%),linear-gradient(180deg,_#f8fafc_0%,_#e2e8f0_100%)] text-slate-900">
      <nav className="flex h-20 items-center justify-between bg-[#F9F8F6] border-b border-cyan-200 px-6 shadow-sm flex-shrink-0">
        {/* Left Section */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <img
              className="h-20 w-20 object-contain "
              src="/image.png"
              alt="Logo"
            />
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
          <div className="relative z-50">
            <img
              className="h-10 w-10 cursor-pointer rounded-full object-cover"
              src="/user.png"
              alt="User"
              onClick={() => setShowAdmin(prev => !prev)}
            />
            {showAdmin && (
              <div className="absolute z-50 mt-1 right-0 top-full rounded-md border border-cyan-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-lg">
                admin
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Main content area - properly constrained */}
      <div className="relative flex flex-1 overflow-hidden">

        <button
          onClick={() => setShowChat((prev) => !prev)}
          className="absolute left-80 top-1/2 z-[1300] flex h-12 w-7 -translate-y-1/2 items-center justify-center rounded-r-xl border border-white/50 bg-white/80 text-lg font-bold text-slate-700 shadow-lg backdrop-blur-md transition-all hover:bg-white"
          aria-label={showChat ? 'Close contextual panel' : 'Open contextual panel'}
        >
          {showChat ? '<' : '>'}
        </button>

        <SidePanel
          lat={lat}
          lon={lon}
          radiusKm={radiusKm}
          locationName={locationName}
          summary={summary}
          isAnalyzing={isAnalyzing}
          isAnalyzed={isAnalyzed}
          onSearch={handleSearch}
          onAnalyze={handleAnalyze}
          onDownload={handleDownload}
          setIsAnalyzing={setIsAnalyzing}
          setIsAnalyzed={setIsAnalyzed}
          setSummary={setSummary}
          setLat={setLat}
          setLon={setLon}
          setLocationName={setLocationName}
          setPoiData={setPoiData}
          setStatus={setStatus}
          setRadiusKm={setRadiusKm}
          setSuggestions={setSuggestions}
          setSessionId={setSessionId}
          addMessage={addMessage}
          setSelectedCategories={setSelectedCategories}
          openContextualPanel={() => setShowChat(true)}
        />
        {showChat && (
          <div className="relative z-30 h-full w-80 shrink-0">
            <ContextualPanel
              setShowChat={setShowChat}
              showChat={showChat}
              selectedCategories={selectedCategories}
            />
          </div>
        )}
        {/* Map container */}
        <div className="relative flex-1 z-0 overflow-hidden">
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
            trigger={showChat}
          />
        </div>



      </div>
    </div>
  )
}
