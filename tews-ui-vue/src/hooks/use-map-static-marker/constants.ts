import pusgenBandaJson from '../../geo-json/pusgen-banda.json'
import pusgenJavaJson from '../../geo-json/pusgen-java.json'
import pusgenKalimantanJson from '../../geo-json/pusgen-kalimantan.json'
import pusgenMalukuJson from '../../geo-json/pusgen-maluku.json'
import pusgenSulawesiJson from '../../geo-json/pusgen-sulawesi.json'
import pusgenSumJson from '../../geo-json/pusgen-sum.json'
import L, { LatLngTuple } from 'leaflet'

export const DEFAULT_MAP_CENTER: LatLngTuple = [-2.5489, 118.0149]
export const DEFAULT_MAP_ZOOM = 5
export const MAP_MAX_ZOOM = 10
export const MAP_MIN_ZOOM = 6
export const INDONESIA_BOUNDS = L.latLngBounds(L.latLng(-11.08, 94.9), L.latLng(5.9, 141.05))

export const ALL_PUSGEN_JSON = [
  pusgenBandaJson,
  pusgenJavaJson,
  pusgenKalimantanJson,
  pusgenMalukuJson,
  pusgenSulawesiJson,
  pusgenSumJson
]
