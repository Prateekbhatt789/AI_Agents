import { useEffect, useState } from 'react'
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
import { fetchDashboardCategories } from '../services/api'



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
                width: 28px;
                height: 28px;
                border-radius: 999px;
                border: 2px solid rgba(255,255,255,0.95);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: ${style.symbol.length > 1 ? '8px' : '12px'};
                font-weight: 700;
                letter-spacing: 0.08em;
                box-shadow: 0 8px 18px rgba(15,23,42,0.22);
                font-family: Inter, system-ui, sans-serif;
            ">
                ${style.symbol}
            </div>
        `,
        iconSize: [16, 16],
        iconAnchor: [14, 14],
        popupAnchor: [0, -14],
    })
}

function normalizeKey(value) {
    return String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[_\s-]+/g, '')
}

function wrapIconHtml(iconHtml) {
    if (!iconHtml) return ''

    const trimmed = String(iconHtml).trim()
    if (trimmed.startsWith('<')) {
        return trimmed
    }

    return `<img src="${trimmed}" alt="icon" style="max-width:100%; max-height:100%; display:block;" />`
}

function createCategoryIcon(category, iconHtml) {
    if (!iconHtml) {
        return createColoredIcon(category)
    }

    const normalized = normalizeKey(category)
    const style = CATEGORY_STYLES[normalized] || { color: '#60a5fa' }
    const htmlContent = wrapIconHtml(iconHtml)

    return L.divIcon({
        className: '',
        html: `
            <div style="
                background: radial-gradient(circle at top, rgba(255,255,255,0.55), transparent 40%), ${style.color};
                width: 30px;
                height: 30px;
                border-radius: 999px;
                border: 2px solid rgba(255,255,255,0.95);
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 8px 18px rgba(15,23,42,0.22);
            ">
                <div style="width: 20px; height: 20px; min-width: 20px; min-height: 20px; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                    ${htmlContent}
                </div>
            </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
        popupAnchor: [0, -15],
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

function parseGeometry(value) {
    if (!value) return null

    if (typeof value === 'string') {
        try {
            return JSON.parse(value)
        } catch {
            return null
        }
    }

    return value
}

function lineCoordinatesToPositions(coordinates) {
    if (!Array.isArray(coordinates)) return []

    return coordinates
        .filter((point) => Array.isArray(point) && point.length >= 2)
        .map(([lng, lat]) => [lat, lng])
}



function getRoadCategory(featureOrRoad) {
    return normalizeKey(
        featureOrRoad?.properties?.category ||
        featureOrRoad?.category ||
        featureOrRoad?.properties?.TYPE ||
        featureOrRoad?.TYPE
    )
}

function getRoadPathOptions(featureOrRoad) {
    const category = getRoadCategory(featureOrRoad)
    const color = category === 'secondary' ? '#22c55e' : '#ef4444'

    return {
        color,
        weight: 3.2,
        opacity: 0.85,
    }
}



function RoadLayer({ roadData = [] }) {

    if (roadData?.type === 'FeatureCollection' || roadData?.type === 'Feature') {
        return (
            <GeoJSON
                data={roadData}
                style={(feature) => getRoadPathOptions(feature)}
            />
        )
    }

    if (!Array.isArray(roadData)) return null

    return roadData.map((road, index) => {

        const geom = parseGeometry(road.geom || road.geometry || road)

        const coordinates =
            geom?.type === 'Feature'
                ? geom.geometry?.coordinates
                : geom?.coordinates

        const type =
            geom?.type === 'Feature'
                ? geom.geometry?.type
                : geom?.type

        if (type === 'LineString') {

            const positions = lineCoordinatesToPositions(coordinates)

            if (!positions.length) return null

            return (
                <Polyline
                    key={road.id || road.road_id || `road-${index}`}
                    positions={positions}
                    pathOptions={getRoadPathOptions(road)}
                />
            )
        }

        if (type === 'MultiLineString') {

            const positions = coordinates
                .map(lineCoordinatesToPositions)
                .filter((line) => line.length > 0)

            if (!positions.length) return null

            return (
                <Polyline
                    key={road.id || road.road_id || `road-${index}`}
                    positions={positions}
                    pathOptions={getRoadPathOptions(road)}
                />
            )
        }

        return null
    })
}

// function RoadLayer({ roadData = [] }) {

//     // FOR GEOJSON RESPONSE
//     if (roadData?.type === 'FeatureCollection' || roadData?.type === 'Feature') {
//         return (
//             <GeoJSON
//                 data={roadData}
//                 style={(feature) => {

//                     const category = getRoadCategory(feature)

//                     console.log("GEOJSON CATEGORY:", category)

//                     // SHOW ONLY PRIMARY ROAD
//                     if (category !== 'primary') {
//                         return {
//                             opacity: 0,
//                             fillOpacity: 0,
//                         }
//                     }

//                     return {
//                         color: '#ef4444',
//                         weight: 5.2,
//                         opacity: 1,
//                     }
//                 }}
//             />
//         )
//     }

//     if (!Array.isArray(roadData)) return null

//     return roadData.map((road, index) => {

//         const category = getRoadCategory(road)

//         console.log("ROAD CATEGORY:", category)

//         // SHOW ONLY PRIMARY ROAD
//         if (category !== 'primary') {
//             return null
//         }

//         const geom = parseGeometry(road.geom || road.geometry || road)

//         const coordinates =
//             geom?.type === 'Feature'
//                 ? geom.geometry?.coordinates
//                 : geom?.coordinates

//         const type =
//             geom?.type === 'Feature'
//                 ? geom.geometry?.type
//                 : geom?.type

//         if (type === 'LineString') {

//             const positions = lineCoordinatesToPositions(coordinates)

//             if (!positions.length) return null

//             return (
//                 <Polyline
//                     key={road.id || road.road_id || `road-${index}`}
//                     positions={positions}
//                     pathOptions={{
//                         color: '#ef4444',
//                         weight: 5.2,
//                         opacity: 1,
//                     }}
//                 />
//             )
//         }

//         if (type === 'MultiLineString') {

//             const positions = coordinates
//                 .map(lineCoordinatesToPositions)
//                 .filter((line) => line.length > 0)

//             if (!positions.length) return null

//             return (
//                 <Polyline
//                     key={road.id || road.road_id || `road-${index}`}
//                     positions={positions}
//                     pathOptions={{
//                         color: '#ef4444',
//                         weight: 5.2,
//                         opacity: 1,
//                     }}
//                 />
//             )
//         }

//         return null
//     })
// }


function ResizeMap({ trigger }) {
    const map = useMap();

    useEffect(() => {
        setTimeout(() => {
            map.invalidateSize();
        }, 300);
    }, [trigger]);

    return null;
}

function LegendControl({ legendItems, selectedCategories, onToggleCategory, onReset }) {
    const map = useMap();

    useEffect(() => {
        if (!legendItems || !legendItems.length) return;

        const control = L.control({ position: 'bottomleft' });

        control.onAdd = function () {
            const container = L.DomUtil.create('div', 'leaflet-bar legend-control');
            container.style.display = 'None';
            container.style.background = 'rgba(255,255,255,0.94)';
            container.style.border = '1px solid rgba(148,163,184,0.25)';
            container.style.borderRadius = '18px';
            container.style.boxShadow = '0 18px 50px rgba(15,23,42,0.12)';
            container.style.padding = '5px 4px';
            container.style.maxWidth = '300px';
            container.style.bottom = '45px';
            container.style.maxHeight = '200px';
            container.style.overflow = 'hidden';
            container.style.fontFamily = 'Inter, system-ui, sans-serif';
            container.style.color = '#0f172a';
            container.style.zIndex = 650;
            container.style.pointerEvents = 'auto';

            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.alignItems = 'center';
            header.style.marginBottom = '10px';

            const title = document.createElement('div');
            title.textContent = 'Layer legend';
            title.style.fontSize = '13px';
            title.style.fontWeight = '700';
            header.appendChild(title);

            const reset = document.createElement('button');
            reset.textContent = 'Reset';
            reset.style.fontSize = '11px';
            reset.style.fontWeight = '700';
            reset.style.color = '#0f172a';
            reset.style.background = 'rgba(241,245,249,0.95)';
            reset.style.border = '1px solid rgba(148,163,184,0.35)';
            reset.style.borderRadius = '999px';
            reset.style.padding = '3px 8px';
            reset.style.cursor = 'pointer';
            reset.addEventListener('click', onReset);
            header.appendChild(reset);
            container.appendChild(header);

            const list = document.createElement('div');
            list.style.maxHeight = '220px';
            list.style.overflowY = 'auto';
            list.style.display = 'grid';
            list.style.gap = '6px';

            legendItems.forEach((item) => {
                const key = item.key;
                const isSelected = selectedCategories.includes(key);

                const itemRow = document.createElement('div');
                itemRow.style.display = 'flex';
                itemRow.style.alignItems = 'center';
                itemRow.style.gap = '10px';
                itemRow.style.padding = '8px 10px';
                itemRow.style.minHeight = '34px';
                itemRow.style.borderRadius = '14px';
                itemRow.style.border = isSelected ? '1px solid #0ea5e9' : '1px solid rgba(148,163,184,0.3)';
                itemRow.style.background = isSelected ? '#eff6ff' : '#f8fafc';
                itemRow.style.color = '#0f172a';
                itemRow.style.cursor = 'pointer';
                itemRow.style.fontSize = '13px';
                itemRow.style.fontWeight = '600';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.checked = isSelected;
                checkbox.style.width = '16px';
                checkbox.style.height = '16px';
                checkbox.style.margin = '0';
                checkbox.style.cursor = 'pointer';
                checkbox.addEventListener('change', () => onToggleCategory(key));
                itemRow.appendChild(checkbox);

                const text = document.createElement('span');
                text.textContent = item.label;
                text.style.flex = '1';
                text.style.whiteSpace = 'nowrap';
                text.style.overflow = 'hidden';
                text.style.textOverflow = 'ellipsis';
                itemRow.appendChild(text);

                itemRow.addEventListener('click', (event) => {
                    if (event.target !== checkbox) {
                        checkbox.checked = !checkbox.checked;
                        onToggleCategory(key);
                    }
                });

                list.appendChild(itemRow);
            });

            container.appendChild(list);
            L.DomEvent.disableClickPropagation(container);
            L.DomEvent.disableScrollPropagation(container);
            return container;
        };

        control.addTo(map);
        return () => control.remove();
    }, [map, legendItems, selectedCategories, onToggleCategory, onReset]);

    return null;
}
export default function MapViewer({
    lat, lon, radiusKm, poiData,
    suggestions,
    onMapClick,
    isAnalyzing, isAnalyzed, trigger,
    gridData = [],
    showGrid = false,
    roadData = [],
    showRoad = false,
    selectedCategories = [],
    setSelectedCategories,
    selectedSubcategories = {},
}) {
    const [categoryIcons, setCategoryIcons] = useState({})
    const [categoryList, setCategoryList] = useState([])

    useEffect(() => {
        let mounted = true

        async function loadCategoryIcons() {
            try {
                const categories = await fetchDashboardCategories()
                if (!mounted) return

                const map = {}
                const list = []
                categories.forEach((item) => {
                    const normalizedKey = normalizeKey(item.label || item.key)
                    const iconValue = item.icon || ''
                    if (iconValue) {
                        map[normalizedKey] = iconValue
                    }

                    list.push({
                        key: normalizedKey,
                        label: item.label || item.key,
                        icon: iconValue,
                    })
                })

                setCategoryIcons(map)
                setCategoryList(list)
            } catch (error) {
                console.error('Failed to load category icons for map markers:', error)
            }
        }

        loadCategoryIcons()

        return () => {
            mounted = false
        }
    }, [])

    const activePoiKeys = poiData?.pois ? Object.keys(poiData.pois).map(normalizeKey) : []
    const legendItems = categoryList.length > 0
        ? categoryList.filter((item) => activePoiKeys.includes(item.key))
        : activePoiKeys.map((categoryKey) => ({
            key: categoryKey,
            label: categoryKey.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
            icon: categoryIcons[categoryKey]
        }))
    const showLegend = poiData?.pois && activePoiKeys.length > 0
    const hasActiveSubcategorySelection = Object.values(selectedSubcategories)
        .some((subcategories) => subcategories.length > 0)

    const resetLegendSelection = () => {
        if (!setSelectedCategories) return
        setSelectedCategories(activePoiKeys)
    }

    const handleToggleCategory = (key) => {
        if (!setSelectedCategories) return
        const nextSelectedCategories = selectedCategories.includes(key)
            ? selectedCategories.filter((k) => k !== key)
            : [...selectedCategories, key]
        setSelectedCategories(nextSelectedCategories)
    }

    return (
        <div className="relative h-full">
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
                {showLegend && (
                    <LegendControl
                        legendItems={legendItems}
                        selectedCategories={selectedCategories}
                        onToggleCategory={handleToggleCategory}
                        onReset={resetLegendSelection}
                    />
                )}
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
                                    Score: {cell.normalized_score}<br />
                                    Population: {cell.population}
                                </Popup>
                            </Polygon>
                        )
                    } catch {
                        return null
                    }
                })}

                {showRoad && <RoadLayer roadData={roadData} />}

                {poiData?.pois && Object.entries(poiData.pois).map(([category, items]) => {
                    if (!Array.isArray(items)) return null

                    const normalizedCategory = normalizeKey(category)
                    const isVisible = selectedCategories.includes(normalizedCategory)
                    if (!isVisible) return null
                    const activeSubcategories = selectedSubcategories[normalizedCategory] || []
                    if (hasActiveSubcategorySelection && activeSubcategories.length === 0) return null

                    const iconHtml = categoryIcons[normalizedCategory]
                    const icon = createCategoryIcon(category, iconHtml)
                    const style = CATEGORY_STYLES[normalizedCategory] || CATEGORY_STYLES[category] || { symbol: 'POI' }
                    const visibleItems = activeSubcategories.length > 0
                        ? items.filter((item) => activeSubcategories.includes(item.sub_category || 'Unknown'))
                        : items

                    return visibleItems.slice(0, 100).map((item, i) => {
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
                                        {normalizedCategory.replace(/_/g, ' ').toUpperCase()}
                                    </small>
                                    {item.sub_category && (
                                        <>
                                            <br />
                                            <small style={{ color: '#0f766e', fontWeight: 600 }}>
                                                Sub-category: {item.sub_category}
                                            </small>
                                        </>
                                    )}
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
        </div>
    )
}
