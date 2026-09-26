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

const qualityParameters = computed(() => [
  { label: 'delay', value: `${stationStatus.value?.delay_second} s` },
  { label: 'rms', value: '.x' },
  { label: 'spikes amplitude', value: stationStatus.value?.spike_amplitude },
  { label: 'spikes count', value: 'x' },
  { label: 'spikes interval', value: 'x' },
  { label: 'timing quality', value: 'xx' }
])

const groundMotions = computed(() => [
  { label: 'acc', value: `${stationStatus.value?.acceleration} µm/s2` },
  { label: 'vel', value: `${stationStatus.value?.velocity} µm/s` },
  { label: 'disp', value: `${stationStatus.value?.displacement} µm/s` }
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
