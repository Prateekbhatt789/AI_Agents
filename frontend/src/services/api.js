const BASE = 'http://127.0.0.1:8000/api'

// ── Session ID — stored after /analyze, sent on every /chat ──
// Also accepts sessionId passed explicitly from App.jsx
let _sessionId = null

// ── Helper: standard POST (no session header) ────────────────
async function post(endpoint, body) {
    const response = await fetch(`${BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Something went wrong')
    }

    return response.json()
}

// ── Helper: POST with session header (for /chat) ─────────────
async function postWithSession(endpoint, body, sessionId = null) {
    // ✅ Use passed sessionId first, fall back to internal _sessionId
    const sid = sessionId || _sessionId

    if (!sid) {
        throw new Error('No session found. Please analyze a location first.')
    }

    const response = await fetch(`${BASE}${endpoint}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Session-Id': sid        // ← attaches session to request
        },
        body: JSON.stringify(body)
    })

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.response || error.detail || 'Something went wrong')
    }

    return response.json()
}

// ── API Functions ─────────────────────────────────────────────

// 1. Search location by name → returns { lat, lon, place_name }
export async function searchLocation(query) {
    return post('/search', { query })
}

// 2. Fetch POIs from OpenStreetMap → returns { hospitals:[], summary:{} }
export async function fetchPOIs(lat, lon, radius_km) {
    return post('/fetch-pois', { lat, lon, radius_km })
}

// 3. Store data in Pinecone + build grid cache
//    Saves session_id returned by backend for all /chat calls
export async function analyzeLocation(location, lat, lon, radius_km, poi_data) {
    const data = await post('/analyze', {
        location, lat, lon, radius_km, poi_data
    })

    // ✅ Save session_id internally as fallback
    if (data.session_id) {
        _sessionId = data.session_id
        console.log('🔍 Session ID saved:', _sessionId)
    }

    return data   // ✅ return full data so App.jsx can also read session_id
}

// 4. Ask AI a question → returns { response, suggestions }
//    Accepts sessionId from App.jsx state
//    Falls back to internally stored _sessionId
//    Returns suggestions array with top 3 locations
export async function chatWithAgent(message, sessionId = null) {
    return postWithSession('/chat', { message }, sessionId)
}

// 5. Download PDF → returns a file blob
export async function exportPDF(location, lat, lon, radius_km, summary) {
    const response = await fetch(`${BASE}/export-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location, lat, lon, radius_km, summary })
    })
    return response.blob()
}

// 6. Reverse geocode — map click coordinates → place name
//    Calls MapTiler directly from frontend (no backend needed)
export async function reverseGeocode(lat, lon) {
    const key = import.meta.env.VITE_MAPTILER_KEY
    const response = await fetch(
        `https://api.maptiler.com/geocoding/${lon},${lat}.json` +
        `?key=${key}&language=en`
    )

    if (!response.ok) {
        throw new Error('Reverse geocoding failed')
    }

    const data = await response.json()

    if (!data.features || data.features.length === 0) {
        throw new Error('No location found at this point')
    }

    return {
        lat,
        lon,
        place_name: data.features[0].place_name
    }
}
