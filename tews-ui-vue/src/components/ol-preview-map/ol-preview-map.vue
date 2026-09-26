<script setup lang="ts">
import { EarthQuakeEvent } from '@src/types/event'
import { Magnitude } from '@src/types/magnitude'
import {
  createEventStationLine,
  createMagnitudeFeature,
  createOpenLayerMap,
  createSelectedEventStationFeatures
} from '@src/utils/ol-map'
import VectorLayer from 'ol/layer/Vector'
import { transform } from 'ol/proj'
import VectorSource from 'ol/source/Vector'
import { onMounted, ref } from 'vue'

const {
  event,
  magnitude,
  fullHeight = false
} = defineProps<{
  event: EarthQuakeEvent
  magnitude: Magnitude
  fullHeight?: boolean
}>()

const mapRef = ref<HTMLDivElement | null>(null)

onMounted(() => {
  const latLng = transform([event.longitude, event.latitude], 'EPSG:4326', 'EPSG:3857')
  const feature = createMagnitudeFeature(event, magnitude)
  feature.setProperties({ event })

  const eventSource = new VectorSource({
    features: [feature]
  })

  const eventLayer = new VectorLayer({
    source: eventSource
  })

  const stationsSource = new VectorSource({
    features: createSelectedEventStationFeatures(event)
  })

  const linesSource = new VectorSource({
    features: createEventStationLine(event)
  })

  const stationsLayer = new VectorLayer({
    source: stationsSource
  })

  const linesLayer = new VectorLayer({
    source: linesSource
  })

  const { map } = createOpenLayerMap(mapRef.value!)
  const view = map.getView()

  map.addLayer(linesLayer)
  map.addLayer(eventLayer)
  map.addLayer(stationsLayer)
  map.getControls().clear()
  view.setCenter(latLng)
  view.setZoom(7)
})
</script>

<template>
  <div
    ref="mapRef"
    class="w-full pointer-events-none"
    :class="{
      'h-full': fullHeight,
      'h-[200px]': !fullHeight
    }" />
</template>
