import { Map } from 'leaflet'
import { ref } from 'vue'

import { ALL_PUSGEN_JSON } from './constants'
import { createPlateBoundariesMarker, createPusgenMarker, createTrenchMarker, createVolcanoMarkers } from './utils'

interface MarkersRef {
  volcanoes: L.GeoJSON | null
  trench: L.GeoJSON | null
  plateBoundaries: L.GeoJSON | null
  pusgen: L.GeoJSON[]
}

function useMapStaticMarker() {
  const alarmActive = ref(false)

  const markersRef = ref<MarkersRef>({
    volcanoes: null,
    trench: null,
    plateBoundaries: null,
    pusgen: []
  })

  const showVolcanoMarkers = (map: Map) => {
    const markers = createVolcanoMarkers()
    markers.addTo(map)
    markersRef.value.volcanoes = markers
  }

  const showTrenchMarker = (map: Map) => {
    const marker = createTrenchMarker()
    marker.addTo(map)
    markersRef.value.trench = marker
  }

  const showPusgenMarkers = (map: Map) => {
    ALL_PUSGEN_JSON.forEach((pusgenJson) => {
      const marker = createPusgenMarker(pusgenJson)
      marker.addTo(map)
      markersRef.value.pusgen.push(marker)
    })
  }

  const showPlateBoundariesMarker = (map: Map) => {
    const marker = createPlateBoundariesMarker()
    marker.addTo(map)
    markersRef.value.plateBoundaries = marker
  }

  const toggleTrench = (enable: boolean, mapCanvas: L.Map) => {
    if (enable) {
      showTrenchMarker(mapCanvas)
    } else {
      markersRef.value.trench?.remove()
      markersRef.value.trench = null
    }
  }

  const toggleVolcano = (enable: boolean, mapCanvas: L.Map) => {
    if (enable) {
      showVolcanoMarkers(mapCanvas)
    } else {
      markersRef.value.volcanoes?.remove()
      markersRef.value.volcanoes = null
    }
  }

  const togglePlateBoundaries = (enable: boolean, mapCanvas: L.Map) => {
    if (enable) {
      showPlateBoundariesMarker(mapCanvas)
    } else {
      markersRef.value.plateBoundaries?.remove()
      markersRef.value.plateBoundaries = null
    }
  }

  const togglePusgen = (enable: boolean, mapCanvas: L.Map) => {
    if (enable) {
      showPusgenMarkers(mapCanvas)
    } else {
      markersRef.value.pusgen.forEach((marker) => {
        // @ts-expect-error
        mapCanvas.removeLayer(marker)
      })
      markersRef.value.pusgen = []
    }
  }

  const onToggleFeatureChange = (mapCanvas: L.Map, name: string, enable: boolean) => {
    switch (name) {
      case 'trench':
        return toggleTrench(enable, mapCanvas)
      case 'volcanoes':
        return toggleVolcano(enable, mapCanvas)
      case 'plateBoundaries':
        return togglePlateBoundaries(enable, mapCanvas)
      case 'pusgen':
        return togglePusgen(enable, mapCanvas)
      case 'alarm':
        alarmActive.value = enable
        return
    }
  }

  return {
    markersRef,
    alarmActive,
    showVolcanoMarkers,
    onToggleFeatureChange
  }
}

export default useMapStaticMarker
