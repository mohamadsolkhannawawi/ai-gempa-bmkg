import L, { LatLngTuple } from 'leaflet'

export const DEFAULT_MAP_CENTER: LatLngTuple = [-2.5489, 118.0149]
export const DEFAULT_MAP_ZOOM = 5
export const MAP_MAX_ZOOM = 9
export const MAP_MIN_ZOOM = 3
export const INDONESIA_BOUNDS = L.latLngBounds(L.latLng(-11.08, 94.9), L.latLng(5.9, 141.05))
export const WORLD_BOUNDS = L.latLngBounds(L.latLng(-90, -180), L.latLng(90, 180))
