import { useEffect } from 'react'
import {
    MapContainer,
    TileLayer,
    Marker,
    Popup,
    Circle,
    Polygon,
    Polyline,
    useMap,
    useMapEvents,
    GeoJSON
} from 'react-leaflet'
import L from 'leaflet'
import '../utils/fixLeafletIcons'
import { delhiBoundaryRing, isWithinDelhiBoundary } from '../utils/delhiBoundary'



const DEFAULT_CENTER = [28.6139, 77.209]
const WORLD_MASK_RING = [
    [90, -180],
    [90, 180],
    [-90, 180],
    [-90, -180],
]
const delhiBoundaryLatLngs = delhiBoundaryRing.map(([lng, lat]) => [lat, lng])

function getBoundaryBounds(latLngs) {
    return latLngs.reduce(
        (bounds, point) => bounds.extend(point),
        L.latLngBounds(latLngs[0], latLngs[0])
    )
}

const delhiBoundaryBounds = delhiBoundaryLatLngs.length
    ? getBoundaryBounds(delhiBoundaryLatLngs)
    : null

function FitToDelhiBoundary({ hasSelectedLocation }) {
    const map = useMap()

    useEffect(() => {
        if (!hasSelectedLocation && delhiBoundaryBounds) {
            map.fitBounds(delhiBoundaryBounds, { padding: [24, 24] })
        }
    }, [hasSelectedLocation, map])

    return null
}

function ConstrainToDelhiExtent() {
    const map = useMap()

    useEffect(() => {
        if (!delhiBoundaryBounds) return

        map.setMaxBounds(delhiBoundaryBounds.pad(0.35))
        map.setMinZoom(10)
    }, [map])

    return null
}

function FlyToLocation({ lat, lon }) {
    const map = useMap()
    useEffect(() => {
        if (lat && lon) map.flyTo([lat, lon], 14, { duration: 1.5 })
    }, [lat, lon, map])
    return null
}

function FlyToSuggestion({ suggestions }) {
    const map = useMap()
    useEffect(() => {
        const best = suggestions?.[0]
        if (best?.lat && best?.lon) {
            map.flyTo([best.lat, best.lon], 15, { duration: 2 })
        }
    }, [suggestions, map])
    return null
}

function MapClickHandler({ onMapClick, isAnalyzing, isAnalyzed, centerLat, centerLon, radiusKm }) {

    function getDistance(lat1, lon1, lat2, lon2) {
        const R = 6371
        const dLat = (lat2 - lat1) * Math.PI / 180
        const dLon = (lon2 - lon1) * Math.PI / 180
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) *
            Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2)
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    }

    const map = useMapEvents({
        click(e) {
            const { lat, lng } = e.latlng

            if (isAnalyzing) return

            if (!isWithinDelhiBoundary(lat, lng)) {
                L.popup()
                    .setLatLng([lat, lng])
                    .setContent(`
                            <div style="padding:6px 8px;text-align:center;font-family:Inter,system-ui,sans-serif;">
                                <strong>Outside Delhi boundary</strong><br/>
                                <small>Please select a point inside the highlighted region</small>
                            </div>
                        `)
                    .openOn(map)
                return
            }

            if (isAnalyzed && centerLat && centerLon && radiusKm) {
                const dist = getDistance(centerLat, centerLon, lat, lng)
                if (dist <= radiusKm) {
                    L.popup()
                        .setLatLng([lat, lng])
                        .setContent(`
                            <div style="padding:6px 8px;text-align:center;font-family:Inter,system-ui,sans-serif;">
                                <strong>Area already analyzed</strong><br/>
                                <small>Click outside the blue circle<br/>to select a new location</small>
                            </div>
                        `)
                        .openOn(map)
                    return
                }
            }

            onMapClick(lat, lng)
        }
    })

    return null
}

const CATEGORY_STYLES = {
    building: { color: '#64748b', symbol: 'BLD' },
    business: { color: '#0ea5e9', symbol: 'BUS' },
    finance: { color: '#22c55e', symbol: '₹' },
    food: { color: '#f43f5e', symbol: 'F' },
    health_care: { color: '#ef4444', symbol: 'HC' },
    infrastructure: { color: '#6b7280', symbol: 'INF' },
    tourism: { color: '#eab308', symbol: 'T' },
    transport: { color: '#3b82f6', symbol: 'TR' },
    recreation: { color: '#10b981', symbol: 'R' },
    shops: { color: '#f59e0b', symbol: 'S' },
    education: { color: '#8b5cf6', symbol: 'ED' },
    religious: { color: '#a855f7', symbol: 'REL' },
}

function createColoredIcon(category) {
    const normalized = category.toLowerCase().replace(/\s+/g, '_')

    const style =
        CATEGORY_STYLES[normalized] ||
        CATEGORY_STYLES[category] ||
        { color: '#60a5fa', symbol: 'POI' }

    return L.divIcon({
        className: '',
        html: `
            <div style="
                background: radial-gradient(circle at top, rgba(255,255,255,0.55), transparent 40%), ${style.color};
                width: 34px;
                height: 34px;
                border-radius: 999px;
                border: 2px solid rgba(255,255,255,0.95);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: ${style.symbol.length > 1 ? '9px' : '13px'};
                font-weight: 700;
                letter-spacing: 0.08em;
                box-shadow: 0 10px 22px rgba(15,23,42,0.28);
                font-family: Inter, system-ui, sans-serif;
            ">
                ${style.symbol}
            </div>
        `,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
        popupAnchor: [0, -17],
    })
}

const RANK_CONFIGS = {
    1: { bg: '#f59e0b', label: '1', size: 46, glow: 'rgba(245,158,11,0.55)' },
    2: { bg: '#94a3b8', label: '2', size: 42, glow: 'rgba(148,163,184,0.45)' },
    3: { bg: '#b45309', label: '3', size: 40, glow: 'rgba(180,83,9,0.45)' },
}

function createRankedIcon(rank) {
    const c = RANK_CONFIGS[rank] || RANK_CONFIGS[1]
    return L.divIcon({
        className: '',
        html: `
            <div style="
                background: radial-gradient(circle at top, rgba(255,255,255,0.55), transparent 42%), ${c.bg};
                border: 3px solid white;
                border-radius: 50%;
                width: ${c.size}px;
                height: ${c.size}px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: ${Math.round(c.size * 0.35)}px;
                font-weight: 800;
                box-shadow: 0 0 0 6px rgba(255,255,255,0.25), 0 18px 36px ${c.glow};
                font-family: Inter, system-ui, sans-serif;
            ">${c.label}</div>
        `,
        iconSize: [c.size, c.size],
        iconAnchor: [c.size / 2, c.size / 2],
        popupAnchor: [0, -(c.size / 2)],
    })
}

const RANK_TITLES = {
    1: 'Best Location',
    2: '2nd Best Location',
    3: '3rd Best Location',
}
function ResizeMap({ trigger }) {
    const map = useMap();

    useEffect(() => {
        setTimeout(() => {
            map.invalidateSize();
        }, 300);
    }, [trigger]);

    return null;
}
export default function MapViewer({
    lat, lon, radiusKm, poiData,
    suggestions,
    onMapClick,
    isAnalyzing, isAnalyzed, trigger,
    gridData = [],
    showGrid = false
}) {
    return (
        <MapContainer
            center={DEFAULT_CENTER}
            zoom={18}
            style={{ width: '100%', height: '100%' }}
            attributionControl={false}
        >
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution="&copy; OpenStreetMap contributors"
            />

            <FitToDelhiBoundary hasSelectedLocation={Boolean(lat && lon)} />
            <ConstrainToDelhiExtent />

            {delhiBoundaryLatLngs.length > 0 && (
                <>
                    <Polygon
                        positions={[WORLD_MASK_RING, delhiBoundaryLatLngs]}
                        pathOptions={{
                            stroke: false,
                            fillColor: '#0f172a',
                            fillOpacity: 0.28,
                            interactive: false,
                        }}
                    />
                    <Polygon
                        positions={delhiBoundaryLatLngs}
                        pathOptions={{
                            color: '#fff7ed',
                            weight: 1.5,
                            opacity: 0.95,
                            fillColor: '#22c55e',
                            fillOpacity: 0.06,
                            interactive: false,
                        }}
                    />
                    <Polyline
                        positions={delhiBoundaryLatLngs}
                        pathOptions={{
                            color: '#f97316',
                            weight: 4,
                            opacity: 0.95,
                            lineCap: 'round',
                            lineJoin: 'round',
                            dashArray: '10 8',
                        }}
                        interactive={false}
                    />
                </>
            )}

            {onMapClick && (
                <MapClickHandler
                    onMapClick={onMapClick}
                    isAnalyzing={isAnalyzing}
                    isAnalyzed={isAnalyzed}
                    centerLat={lat}
                    centerLon={lon}
                    radiusKm={radiusKm}
                />
            )}

            {lat && lon && <FlyToLocation lat={lat} lon={lon} />}
            <ResizeMap trigger={trigger} />
            {suggestions && suggestions.length > 0 && (
                <FlyToSuggestion suggestions={suggestions} />
            )}

            {lat && lon && (
                <Marker position={[lat, lon]}>
                    <Popup>
                        <strong>Selected Location</strong><br />
                        {lat.toFixed(4)}, {lon.toFixed(4)}
                    </Popup>
                </Marker>
            )}

            {lat && lon && radiusKm && (
                <Circle
                    center={[lat, lon]}
                    radius={radiusKm * 1000}
                    pathOptions={{
                        color: '#0891b2',
                        weight: isAnalyzed ? 2 : 1,
                        fillColor: '#22d3ee',
                        fillOpacity: isAnalyzed ? 0.1 : 0.06
                    }}
                />
            )}

            {showGrid && gridData.map((cell) => {
                try {
                    const geom = typeof cell.geom === 'string' ? JSON.parse(cell.geom) : cell.geom
                    const positions = geom.coordinates[0].map(([lng, lat]) => [lat, lng])
                    const opacity = Math.min(cell.score / 100, 1)
                    { console.log('showGrid:', showGrid, 'gridData length:', gridData?.length, 'sample:', gridData?.[0]) }

                    return (
                        <Polygon
                            key={cell.grid_id}
                            positions={positions}
                            pathOptions={{
                                color: '#0891b2',
                                weight: 0.8,
                                fillColor: `hsl(${Math.round(opacity * 120)}, 80%, 45%)`,
                                fillOpacity: 0.35,
                            }}
                        >
                            <Popup>
                                <strong>Grid {cell.grid_id}</strong><br />
                                Score: {cell.score}<br />
                                Population: {cell.population}
                            </Popup>
                        </Polygon>
                    )
                } catch {
                    return null
                }
            })}

            {poiData?.pois && Object.entries(poiData.pois).map(([category, items]) => {
                if (!Array.isArray(items)) return null

                const icon = createColoredIcon(category)
                const style = CATEGORY_STYLES[category] || { symbol: 'POI' }

                return items.slice(0, 100).map((item, i) => {
                    if (!item.lat || !item.lon) return null

                    return (
                        <Marker
                            key={`${category}-${i}`}
                            position={[item.lat, item.lon]}
                            icon={icon}
                        >
                            <Popup>
                                <strong>{style.symbol} {item.name || "Unknown"}</strong><br />
                                <small style={{ color: '#64748b' }}>
                                    {category.toUpperCase()}
                                </small>
                            </Popup>
                        </Marker>
                    )
                })
            })}

            {suggestions && suggestions.map(s => (
                s?.lat && s?.lon ? (
                    <Marker
                        key={`suggestion-${s.rank}`}
                        position={[s.lat, s.lon]}
                        icon={createRankedIcon(s.rank)}
                    >
                        <Popup>
                            <strong>
                                {RANK_TITLES[s.rank] || `Option ${s.rank}`}
                            </strong><br />
                            <small style={{ color: '#475569' }}>
                                {s.label}
                            </small><br /><br />
                            {s.notes?.map((note, i) => (
                                <span key={i} style={{ fontSize: '12px' }}>
                                    {note}<br />
                                </span>
                            ))}
                            <br />
                            <small style={{ color: '#94a3b8' }}>
                                {s.lat?.toFixed(4)}, {s.lon?.toFixed(4)}
                            </small>
                        </Popup>
                    </Marker>
                ) : null
            ))}

            <div className='absolute bottom-2 right-2 z-[1000] flex items-center gap-1 bg-black/80 backdrop-blur-sm rounded-full text-white px-4 py-1.5 text-xs shadow-lg border border-white/10'>
                <span className="opacity-80">Powered By</span>
                <span className="font-bold tracking-wide">ML Infomap</span>
            </div>
        </MapContainer>
    )
}
