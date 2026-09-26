<script setup lang="ts">
import { InformationList } from '@src/components/information-list'
import { OLPreviewMap } from '@src/components/ol-preview-map'
import { EarthQuakeEvent } from '@src/types/event'
import { Magnitude } from '@src/types/magnitude'
import { formatDate } from '@src/utils/string'

import { MockChart } from '../mock-chart'

const { magnitudes, event } = defineProps<{
  event: EarthQuakeEvent
  magnitudes: Magnitude[]
}>()

const values = magnitudes.map((magnitude) => magnitude.value)
const selectedMagnitude = magnitudes[0]
const informations = [
  {
    label: 'Time:',
    value: formatDate(event.created_at),
    width: '100px'
  },
  {
    label: 'Count:',
    value: magnitudes.length
  },
  {
    label: 'Min:',
    value: Math.min(...values)
  },
  {
    label: 'Max:',
    value: Math.max(...values)
  }
]

// TODO: this is mock data
const additionalInformations = [
  {
    label: 'Agency:',
    value: 'xxx',
    width: '100px'
  },
  {
    label: 'Author:',
    value: 'xxx'
  },
  {
    label: 'Evaluation:',
    value: 'x (A)'
  },
  {
    label: 'Method:',
    value: 'xxx'
  }
]
</script>

<template>
  <div class="flex gap-4 max-md:flex-col">
    <div class="w-[30%] flex flex-col gap-2 max-md:w-full">
      <div class="text-white">{{ event.region }} Region</div>
      <div class="relative pb-[100%]">
        <OLPreviewMap
          v-if="selectedMagnitude"
          :magnitude="selectedMagnitude"
          :event="event"
          class="absolute w-full h-full" />
      </div>
    </div>
    <div class="flex-1 flex flex-col">
      <div class="flex-1">
        <InformationList :informations="informations" />
      </div>
      <div class="divider" />
      <InformationList :informations="additionalInformations" />
    </div>
    <div class="w-[30%] max-md:w-full">
      <MockChart />
    </div>
  </div>
</template>
