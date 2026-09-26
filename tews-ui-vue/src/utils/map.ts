import { EarthQuakeEvent } from '@src/types/event'
import { Magnitude } from '@src/types/magnitude'
import { Station } from '@src/types/station'
import { WSEvent } from '@src/types/ws-event'
import L, { LatLngTuple } from 'leaflet'

import { DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM, MAP_MAX_ZOOM, MAP_MIN_ZOOM, WORLD_BOUNDS } from '../constants/map'
import { hexToRGB } from './color'
import { getDepthColor, getMagnitudeWidth } from './event'

const renderer = L.canvas()
const pulseIcon = L.icon({ iconUrl: '/images/pulse.webp', iconSize: [14, 14] })

export const createMapCanvas = (id: string, options?: L.MapOptions) => {
  const createdMap = L.map(id, {
    renderer,
    attributionControl: false,
    zoomControl: false,
    markerZoomAnimation: false,
    maxBoundsViscosity: 1.0,
    doubleClickZoom: false,
    minZoom: MAP_MIN_ZOOM,
    maxZoom: MAP_MAX_ZOOM,
    maxBounds: WORLD_BOUNDS,
    preferCanvas: true,
    layers: [
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}')
    ],
    ...options
  })

  createdMap.setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM)

  return createdMap
}

export const generateStationIcon = (code: string, hasPick: boolean) => {
  return L.divIcon({
    iconSize: [26, 30],
    html: `<div class="station-icon ${hasPick ? 'station-icon-with-pick' : ''}"><div class="station-name">${code}</div></div>`
  })
}

export const createStationMarker = (station: Station, hasPick: boolean) => {
  const lat = Number(station.latitude)
  const lng = Number(station.longitude)

  if (!lat || !lng || isNaN(lat) || isNaN(lng)) {
    return null
  }

  const marker = L.marker([Number(station.latitude), Number(station.longitude)], {
    icon: generateStationIcon(station.code, hasPick),
    station
  })

  return marker
}

export const createEventMarker = (event: Pick<WSEvent, 'latitude' | 'longitude'>) => {
  const latLng: LatLngTuple = [event.latitude, event.longitude]
  const marker = L.marker(latLng, {
    icon: pulseIcon
  })
  return marker
}

export const createMagnitudeMarker = (event: EarthQuakeEvent, magnitude: Magnitude) => {
  const latLng: LatLngTuple = [event.latitude, event.longitude]
  const width = getMagnitudeWidth(magnitude.value)
  const color = getDepthColor(event.depth)
  const marker = L.marker(latLng, {
    icon: L.divIcon({
      iconSize: [width, width],
      html: `<div style="background-color: ${hexToRGB(color, 0.5)}; width: ${width}px; height: ${width}px; border-radius: 100%; border: 1px solid ${color};"></div>`
    })
  })
  return marker
}

export const createClusterIcon = (count: number, hasPick: boolean) => {
  return L.divIcon({
    iconSize: [26, 30],
    html: `<div class="station-icon ${hasPick ? 'station-icon-with-pick' : ''}"><div>${count}</div></div>`
  })
}
