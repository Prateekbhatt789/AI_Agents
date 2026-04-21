import boundaryRaw from '../assets/Delhi_bnd.geojson?raw'
import { point, booleanPointInPolygon } from '@turf/turf'

const boundaryGeoJson = JSON.parse(boundaryRaw)

function closeRing(coordinates) {
  if (!coordinates?.length) return []

  const [firstLng, firstLat] = coordinates[0]
  const [lastLng, lastLat] = coordinates[coordinates.length - 1]

  if (firstLng === lastLng && firstLat === lastLat) {
    return coordinates
  }

  return [...coordinates, coordinates[0]]
}

function getBoundaryRing(featureCollection) {
  const boundaryFeature = featureCollection?.features?.[0]
  const lineCoordinates = boundaryFeature?.geometry?.coordinates?.[0] ?? []
  return closeRing(lineCoordinates)
}

export const delhiBoundaryRing = getBoundaryRing(boundaryGeoJson)
export const delhiBoundaryPolygon = {
  type: 'Feature',
  properties: boundaryGeoJson?.features?.[0]?.properties ?? {},
  geometry: {
    type: 'Polygon',
    coordinates: [delhiBoundaryRing],
  },
}

export function isWithinDelhiBoundary(lat, lon) {
  if (lat == null || lon == null || !delhiBoundaryRing.length) return false
  return booleanPointInPolygon(point([lon, lat]), delhiBoundaryPolygon)
}
