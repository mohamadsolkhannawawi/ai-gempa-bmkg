<script setup lang="ts">
import { InformationList } from '@src/components/information-list'
import { PickingArrivalWaveformItem } from '@src/domain/picking/picking-arrival-waveform-item'
import { TimestampAxis } from '@src/domain/trace-view/timestamp-axis'
import useGetEventDetail from '@src/hooks/use-get-event-detail'
import { Arrival } from '@src/types/arrival'
import { EarthQuakeEvent } from '@src/types/event'
import { Station } from '@src/types/station'
import { formatDate, getOriginTimeFromEvent, newISODate } from '@src/utils/string'
import * as d3 from 'd3'
import { addMinutes, subMinutes } from 'date-fns'
import { computed, ref, watch } from 'vue'

const { event } = defineProps<{
  event: EarthQuakeEvent
}>()

defineEmits<{
  (e: 'close'): void
}>()

const { data: eventDetail, isLoading: isEventDetailLoading } = useGetEventDetail(event._id)

const arrivals = computed(() => eventDetail.value?.arrivals ?? [])

const mappedArrival = computed(() =>
  arrivals.value.reduce<Record<string, { station: Station; arrivals: Arrival[] }>>((curr, arrival) => {
    if (!curr[arrival.pick_details._id]) {
      curr[arrival.pick_details._id] = {
        station: arrival.station_details,
        arrivals: [arrival]
      }
    } else {
      curr[arrival.pick_details._id].arrivals.push(arrival)
    }
    return curr
  }, {})
)
const originTime = computed(() =>
  eventDetail.value ? newISODate(eventDetail.value.cluster_detail[0].origin_time) : null
)
const startTime = computed(() => (originTime.value ? subMinutes(originTime.value, 5) : null))
const endTime = computed(() => (originTime.value ? addMinutes(originTime.value, 5) : null))
const container = ref<HTMLDivElement | null>(null)
const width = ref<number | null>(null)
const xScale = ref<d3.ScaleTime<number, number, never> | null>(null)
const magnitude = computed(() => eventDetail.value?.magnitudes.find((m) => m.type.toLowerCase() === 'mw'))
const informations = computed(() => [
  {
    label: 'Mag:',
    value: magnitude?.value?.value ?? '-'
  },
  {
    label: 'Depth:',
    value: event.depth
  },
  {
    label: 'Time:',
    value: formatDate(getOriginTimeFromEvent(event))
  },
  {
    label: 'Location:',
    value: `${event.latitude}, ${event.longitude}`
  }
])

watch(
  [container, startTime, endTime],
  ([newContainer, newStartTime, newEndTime]) => {
    if (newContainer && newStartTime && newEndTime) {
      const newWidth = newContainer.clientWidth - 24
      width.value = newWidth
      xScale.value = d3.scaleUtc().domain([newStartTime.getTime(), newEndTime.getTime()]).range([0, newWidth])
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="drawer z-10">
    <input type="checkbox" class="drawer-toggle" :checked="true" />
    <div class="drawer-side w-auto">
      <!-- <label aria-label="close sidebar" class="drawer-overlay" @click="$emit('close')" /> -->

      <div class="flex flex-col w-full h-full overflow-hidden max-w-md bottom-0 left-0 fixed z-[9999] bg-base-300">
        <div class="flex items-center gap-2 justify-between p-3 bg-white/5">
          <div class="truncate">{{ event.name }}</div>
          <button class="btn btn-xs btn-error" @click="$emit('close')">
            <v-icon name="md-close" />
          </button>
        </div>

        <div class="p-3 border-b">
          <InformationList :informations="informations" />
        </div>

        <div ref="container" class="flex-1 h-full overflow-hidden">
          <div v-if="isEventDetailLoading">Loading...</div>
          <div
            v-else-if="!!originTime && !!endTime && !!startTime && !!width && !!xScale"
            class="p-3 flex flex-col h-full">
            <div class="flex-1 h-full overflow-y-auto">
              <PickingArrivalWaveformItem
                v-for="(arrival, index) in Object.values(mappedArrival)"
                :key="index"
                :selected="false"
                :width="width"
                :origin-time="originTime"
                :start-time="startTime"
                :end-time="endTime"
                :station="arrival.station"
                :arrivals="arrival.arrivals"
                :x-scale="xScale" />
            </div>
            <TimestampAxis
              :width="width"
              :start-time="startTime.getTime()"
              :end-time="endTime.getTime()"
              time-format="%M:%S" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
