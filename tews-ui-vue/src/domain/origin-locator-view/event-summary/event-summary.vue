<script setup lang="ts">
import { InformationList } from '@src/components/information-list'
import { OLPreviewMap } from '@src/components/ol-preview-map'
import { EarthQuakeEvent } from '@src/types/event'
import {
  formatDate,
  formatDepth,
  formatMagnitude,
  getDefaultMagnitude,
  getOriginTimeFromEvent
} from '@src/utils/string'
import { computed } from 'vue'

const { event } = defineProps<{
  event: EarthQuakeEvent
}>()

const magnitude = computed(() => getDefaultMagnitude(event.magnitudes) ?? event.magnitudes[0])

// TODO: this is mock
const informations = [
  {
    label: 'MLv',
    value: '.x (x)'
  },
  {
    label: 'M',
    value: '.x (x)'
  },
  {
    label: 'Phases',
    value: 'xx'
  },
  {
    label: 'RMS Res',
    value: '0.x s'
  },
  {
    label: 'Event ID',
    value: 'xxx'
  },
  {
    label: 'Agency ID',
    value: 'xxx'
  }
]
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="text-slate-200 font-semibold">{{ formatDate(getOriginTimeFromEvent(event)) }}</div>
    <div class="text-slate-200 font-semibold">M {{ formatMagnitude(magnitude?.value) }}</div>
    <div class="text-slate-200 font-semibold">{{ event.region }} Region</div>
    <div class="text-slate-200 font-semibold">Depth {{ formatDepth(event.depth) }}km</div>

    <OLPreviewMap :event="event" :magnitude="magnitude" />

    <InformationList :informations="informations" />
  </div>
</template>
