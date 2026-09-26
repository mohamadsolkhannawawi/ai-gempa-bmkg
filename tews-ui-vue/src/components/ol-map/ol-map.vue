<script setup lang="ts">
import 'ol/ol.css'
import './style.css'

import { MapConfigDrawer } from '@src/components/map-config-drawer'
import useEventSocket from '@src/hooks/use-event-socket'
import { WSEvent } from '@src/types/ws-event'
import { speakAlarm } from '@src/utils/alarm'
import {
  createEventMarker,
  createOpenLayerMap,
  createPlateBoundariesLayers,
  createPusgenLayers,
  createTrenchLayers,
  createVolcanoLayers,
  flashEventMarker
} from '@src/utils/ol-map'
import { Feature, Map, MapBrowserEvent } from 'ol'
import { Geometry } from 'ol/geom'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import { fromLonLat } from 'ol/proj'
import { XYZ } from 'ol/source'
import VectorSource from 'ol/source/Vector'
import { onMounted, reactive, ref } from 'vue'
import { toast } from 'vue3-toastify'

defineProps<{
  isSettingsOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close-settings'): void
  (e: 'map-created', map: Map): void
  (e: 'map-click', event: MapBrowserEvent<any>): void
  (e: 'new-event'): void
}>()

useEventSocket((eventData) => handleEvent(eventData))

const eventSource = new VectorSource()
const eventLayer = new VectorLayer({
  source: eventSource
})

const mapDiv = ref<null | HTMLDivElement>(null)
const map = ref<null | Map>(null)
const tileLayer = ref<TileLayer<XYZ> | null>(null)
const layers = reactive<{
  volcanoes: VectorLayer<Feature<Geometry>> | null
  plateBoundaries: VectorLayer<Feature<Geometry>> | null
  trench: VectorLayer<Feature<Geometry>> | null
  pusgen: VectorLayer<Feature<Geometry>>[]
}>({
  volcanoes: null,
  plateBoundaries: null,
  trench: null,
  pusgen: []
})
const settingsValue = reactive({
  volcanoes: true,
  trench: false,
  plateBoundaries: false,
  pusgen: false
})

const handleEvent = (event: WSEvent) => {
  emit('new-event')

  // TODO: add event to map
  if (!map.value) return

  const marker = createEventMarker(event)
  eventLayer.getSource()?.addFeature(marker)

  speakAlarm(event)

  toast.error(`Terdeteksi gempa di ${event.sub_region}, ${event.region}. Klik untuk melihat lokasi gempa.`, {
    autoClose: 10_000,
    position: 'bottom-center',
    onClick: () => {
      map.value?.getView().animate({
        center: fromLonLat([event.longitude, event.latitude]),
        zoom: 7,
        duration: 600
      })
    }
  })

  setTimeout(() => {
    eventLayer.getSource()?.removeFeature(marker)
  }, 20_000)
}

const onSettingValueChange = (name: keyof typeof settingsValue, value: boolean) => {
  if (!map.value) return

  settingsValue[name] = value

  switch (name) {
    case 'volcanoes': {
      layers.volcanoes?.setVisible(value)
      break
    }
    case 'plateBoundaries': {
      layers.plateBoundaries?.setVisible(value)
      break
    }
    case 'trench': {
      layers.trench?.setVisible(value)
      break
    }
    case 'pusgen': {
      layers.pusgen.forEach((pusgen) => {
        pusgen.setVisible(value)
      })
      break
    }
  }
}

onMounted(() => {
  if (!mapDiv.value) return
  const { map: createdMap, tileLayer: createdTileLayer } = createOpenLayerMap(mapDiv.value)
  const volcanoLayers = createVolcanoLayers()
  const plateBoundariesLayers = createPlateBoundariesLayers()
  const trenchLayers = createTrenchLayers()
  const pusgenLayers = createPusgenLayers()

  createdMap.addLayer(volcanoLayers)
  createdMap.addLayer(plateBoundariesLayers)
  createdMap.addLayer(trenchLayers)
  createdMap.addLayer(eventLayer)

  pusgenLayers.forEach((pusgenLayer) => {
    createdMap.addLayer(pusgenLayer)
  })

  emit('map-created', createdMap)

  map.value = createdMap
  tileLayer.value = createdTileLayer
  layers.volcanoes = volcanoLayers
  layers.plateBoundaries = plateBoundariesLayers
  layers.trench = trenchLayers
  layers.pusgen = pusgenLayers

  createdMap.on('click', (event) => emit('map-click', event))
  eventSource.on(
    'addfeature',
    (event) => !!event.feature && flashEventMarker(event.feature, createdTileLayer, createdMap)
  )
})
</script>

<template>
  <div ref="mapDiv" class="w-full h-full flex-1" />

  <MapConfigDrawer
    v-if="isSettingsOpen"
    :value="settingsValue"
    @close="$emit('close-settings')"
    @change="onSettingValueChange" />
</template>
