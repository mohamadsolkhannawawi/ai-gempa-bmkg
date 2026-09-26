<script setup lang="ts">
import { InformationList } from '@src/components/information-list'
import { OLPreviewMap } from '@src/components/ol-preview-map'
import { EarthQuakeEvent } from '@src/types/event'
import { formatDate } from '@src/utils/string'
import { computed } from 'vue'

import { ArrivalList } from '../arrival-list'
import { ChartTabList } from '../chart-tab-list'

const { event } = defineProps<{
  event: EarthQuakeEvent
}>()

const magnitude = computed(() => event.magnitudes.find((info) => info.type.toLowerCase() === 'mw'))

const informations = [
  {
    label: 'Time:',
    value: formatDate(event.cluster_detail[0]?.origin_time),
    width: '100'
  },
  {
    label: 'Depth:',
    value: event.depth
  },
  {
    label: 'Lat:',
    value: event.latitude
  },
  {
    label: 'Lon:',
    value: event.longitude
  },
  // TODO: this is mock
  {
    label: 'Phases:',
    value: 'xx/xx'
  },
  {
    label: 'RMS Res:',
    value: '.x s'
  },
  {
    label: 'Az Gap:',
    value: 'xxx°'
  },
  {
    label: 'Min Dist:',
    value: '.x°'
  }
]

// TODO: this is mock
const additionalInformations = [
  {
    label: 'EventID:',
    value: 'xxx',
    width: '100'
  },
  {
    label: 'Agency:',
    value: 'xxx'
  },
  {
    label: 'Author:',
    value: 'xxx_xx'
  },
  {
    label: 'Evaluation:',
    value: 'x (A)'
  },
  {
    label: 'Method:',
    value: 'xxx'
  },
  {
    label: 'Earth model:',
    value: 'xxx'
  },
  {
    label: 'Updated:',
    value: 'xxxx-xx-xx xx:xx:xx'
  }
]
</script>

<template>
  <div class="flex-1 flex flex-col gap-4 w-full h-full">
    <div class="flex gap-4 max-md:grid-cols-1 max-md:flex-col">
      <div class="w-[30%] max-md:w-full">
        <div class="pb-[100%] relative">
          <OLPreviewMap
            v-if="magnitude"
            :event="event"
            :magnitude="magnitude"
            :full-height="true"
            class="absolute w-full h-full max-md:w-full" />
        </div>
      </div>
      <div class="flex-1 flex flex-col">
        <InformationList :informations="informations" />
        <div class="divider" />
        <InformationList :informations="additionalInformations" />
      </div>
      <div class="w-[27%] max-md:w-full">
        <ChartTabList />
      </div>
    </div>

    <ArrivalList :event="event" />
  </div>
</template>
