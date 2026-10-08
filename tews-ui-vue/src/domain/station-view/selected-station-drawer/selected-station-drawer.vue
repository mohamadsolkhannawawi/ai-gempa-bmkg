<script setup lang="ts">
import useGetStationWaveformStatus from '@src/hooks/use-get-station-waveform-status'
import { Station } from '@src/types/station'
import { computed } from 'vue'

import { SelectedStationWaveformList } from '../selected-station-waveform-list'
import DrawerContent from './drawer-content.vue'
import DrawerTitle from './drawer-title.vue'
import StationInformationItems from './station-information-items.vue'

const { station } = defineProps<{
  station: Station
}>()

const { data } = useGetStationWaveformStatus(station._id)
const stationStatus = computed(() => data.value?.data)

// Helper to safely format numeric values with fallback
const fmt = (v: number | null | undefined, unit: string) => {
  if (v === undefined || v === null || Number.isNaN(v)) return `- ${unit}`
  return `${v.toFixed(2)} ${unit}`
}

const qualityParameters = computed(() => [
  { label: 'delay', value: fmt(stationStatus.value?.delay_second, 's') },
  { label: 'rms', value: '- -' },
  { label: 'spikes amplitude', value: fmt(stationStatus.value?.spike_amplitude, '') },
  { label: 'spikes count', value: '- -' },
  { label: 'spikes interval', value: '- -' },
  { label: 'timing quality', value: '- -' }
])

const groundMotions = computed(() => [
  { label: 'acc', value: fmt(stationStatus.value?.acceleration, 'µm/s²') },
  { label: 'vel', value: fmt(stationStatus.value?.velocity, 'µm/s') },
  { label: 'disp', value: fmt(stationStatus.value?.displacement, 'µm') }
])

const emit = defineEmits<{
  (e: 'close'): void
}>()
</script>

<template>
  <div class="drawer z-[99999]">
    <input checked type="checkbox" class="drawer-toggle" />
    <div class="drawer-side">
      <label aria-label="close sidebar" class="drawer-overlay" @click="emit('close')" />
      <div id="selected-station-drawer" class="w-full max-w-sm h-full bg-base-100 flex flex-col">
        <DrawerTitle>
          <div class="flex justify-between items-center">
            <div>{{ station.code }}</div>
            <button class="btn btn-xs btn-error" @click="emit('close')">
              <v-icon name="md-close" />
            </button>
          </div>
        </DrawerTitle>

        <div class="flex-1 overflow-y-auto">
          <DrawerContent>{{ station.name }}</DrawerContent>

          <DrawerTitle>Quality Parameters</DrawerTitle>
          <DrawerContent>
            <StationInformationItems :items="qualityParameters" />
          </DrawerContent>

          <DrawerTitle>Ground Motion</DrawerTitle>
          <DrawerContent>
            <StationInformationItems :items="groundMotions" />
          </DrawerContent>

          <SelectedStationWaveformList :station="station" />
        </div>
      </div>
    </div>
  </div>
</template>
