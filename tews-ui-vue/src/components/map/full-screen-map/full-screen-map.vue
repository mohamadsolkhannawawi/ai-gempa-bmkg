<script setup lang="ts">
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import './styles.css'

import { MapConfigDrawer } from '@src/components/map-config-drawer'
import useEventSocket from '@src/hooks/use-event-socket'
import useMapStaticMarker from '@src/hooks/use-map-static-marker'
import { WSEvent } from '@src/types/ws-event'
import { speakAlarm } from '@src/utils/alarm'
import { Map } from 'leaflet'
import { onMounted, reactive, ref } from 'vue'
import { toast } from 'vue3-toastify'

import { createEventMarker, createMapCanvas } from '../../../utils/map'

const { showVolcanoMarkers, onToggleFeatureChange } = useMapStaticMarker()
useEventSocket((eventData) => handleEvent(eventData))

defineProps<{
  isSettingsOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close-settings'): void
  (e: 'map-created', map: Map): void
  (e: 'new-event'): void
}>()

const map = ref<Map | null>(null)
const settingsValue = reactive({
  volcanoes: true,
  trench: false,
  plateBoundaries: false,
  pusgen: false
})

const handleEvent = (event: WSEvent) => {
  emit('new-event')

  if (!map.value) return

  const marker = createEventMarker(event)

  marker.addTo(map.value as Map)

  speakAlarm(event)

  toast.error(`Terdeteksi gempa dari stasiun ${event.cluster.station}. Klik untuk melihat lokasi gempa.`, {
    autoClose: 10_000,
    position: 'bottom-center',
    onClick: () => {
      map.value?.flyTo([event.latitude, event.longitude], 8, {
        animate: false
      })
    }
  })

  setTimeout(() => {
    map.value?.removeLayer(marker)
  }, 20_000)
}

const onSettingValueChange = (name: keyof typeof settingsValue, value: boolean) => {
  if (map.value) {
    onToggleFeatureChange(map.value as Map, name, value)
    settingsValue[name] = value
  }
}

onMounted(() => {
  const createdMap = createMapCanvas('map')
  showVolcanoMarkers(createdMap)
  emit('map-created', createdMap)
  map.value = createdMap
})
</script>

<template>
  <div id="map" class="w-full h-full flex-1" />
  <MapConfigDrawer
    v-if="isSettingsOpen"
    :value="settingsValue"
    @close="$emit('close-settings')"
    @change="onSettingValueChange" />
</template>
