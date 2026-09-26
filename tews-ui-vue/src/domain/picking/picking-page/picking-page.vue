<script setup lang="ts">
import { TRACEVIEW_FILTERED_CHANNEL } from '@src/constants/waveform'
import { usePickerStore } from '@src/stores/picker'
import { Arrival } from '@src/types/arrival'
import { EarthQuakeEvent } from '@src/types/event'
import { Station } from '@src/types/station'
import { OrderPhaseType, PhaseType } from '@src/types/waveform'
import { newISODate } from '@src/utils/string'
import * as d3 from 'd3'
import { addMilliseconds, addMinutes, differenceInMilliseconds, differenceInMinutes, subMinutes } from 'date-fns'
import { intersection, union } from 'lodash'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { ArrivalPickerWaveformItem } from '../arrival-picker-waveform-item'
import { PickingArrivalWaveformItem } from '../picking-arrival-waveform-item'
import { PickingFilter } from '../picking-filter'

interface SelectedArrival {
  p?: Arrival
  s?: Arrival
}

interface StationAndArrival {
  station: Station
  arrivals: SelectedArrival
  updatedArrivals: SelectedArrival
}

type PickId = string

const { event } = defineProps<{
  event: EarthQuakeEvent
}>()

const router = useRouter()

const goBack = () => {
  router.back()
}

const pickerStore = usePickerStore()

const container = ref<HTMLDivElement | null>(null)
const arrivals = computed(() => event.arrivals ?? [])
const originTime = newISODate(event.cluster_detail[0].origin_time)
const startTime = ref<Date | null>(null)
const endTime = ref<Date | null>(null)
const diffTime = ref<number | null>(null)
const width = ref<number | null>(null)
const xScale = ref<d3.ScaleTime<number, number, never> | null>(null)
const selectedPhase = ref<PhaseType>('P')
const orderPhase = ref<OrderPhaseType>('OT')
const arrivalByPickId = ref<Record<PickId, StationAndArrival>>({})
const selectedPickId = ref<PickId | null>(null)
const selectedArrivalByPickId = ref<StationAndArrival | null>(null)

const selectedStation = computed<Station | null>(() => {
  if (!selectedArrivalByPickId.value) return null
  const station = selectedArrivalByPickId.value.station
  const firstChannels = intersection(station.channel, TRACEVIEW_FILTERED_CHANNEL)
  const otherChannels = union(firstChannels, station.channel)

  return {
    ...station,
    channel: otherChannels.slice(0, 3)
  }
})

const getMinDateBetween = (dateA: number, dateB?: string) => {
  if (!dateB) return dateA
  return new Date(dateB).getTime() < dateA ? new Date(dateB).getTime() : dateA
}

const firstPoint = computed(() => {
  const values = Object.values(arrivalByPickId.value)

  let firstP = Infinity
  let firstS = Infinity

  for (const value of values) {
    firstP = getMinDateBetween(firstP, value.arrivals.p?.timestamp)
    firstS = getMinDateBetween(firstS, value.arrivals.s?.timestamp)
  }

  return {
    firstP,
    firstS
  }
})

const joinPSArrival = ({ p, s }: SelectedArrival): Arrival[] => {
  const joinedArrivals: Arrival[] = []
  if (p) joinedArrivals.push(p)
  if (s) joinedArrivals.push(s)
  return joinedArrivals
}

const onConfirm = () => {
  const arrivalWithUpdatedPick: Record<PickId, SelectedArrival> = {}

  Object.keys(arrivalByPickId.value)
    .filter((pickId) => Object.keys(arrivalByPickId.value[pickId]?.updatedArrivals ?? {}).length > 0)
    .forEach((pickId) => {
      arrivalWithUpdatedPick[pickId] = arrivalByPickId.value[pickId].updatedArrivals
    })

  pickerStore.updateEventPick({
    [event._id]: arrivalWithUpdatedPick
  })

  goBack()
}

const onSelectStation = (pickId: PickId) => {
  selectedArrivalByPickId.value = arrivalByPickId.value[pickId]
  selectedPickId.value = pickId
}

const onChangePhase = (date: Date) => {
  if (!selectedPickId.value || !selectedArrivalByPickId.value) return

  const newUpdatedArrival = { ...arrivalByPickId.value[selectedPickId.value] }

  if (selectedPhase.value === 'P') {
    newUpdatedArrival.updatedArrivals.p = {
      ...newUpdatedArrival.arrivals.p!,
      timestamp: date.toISOString()
    }
  } else {
    newUpdatedArrival.updatedArrivals.s = {
      ...newUpdatedArrival.arrivals.s!,
      timestamp: date.toISOString()
    }
  }

  arrivalByPickId.value[selectedPickId.value] = newUpdatedArrival
  selectedArrivalByPickId.value = newUpdatedArrival
}

const getStartTimeByPhase = (stationAndArrival: StationAndArrival) => {
  const firstP = firstPoint.value.firstP
  const firstS = firstPoint.value.firstS
  const arrivalP = stationAndArrival.arrivals.p?.timestamp
  const arrivalS = stationAndArrival.arrivals.s?.timestamp

  if (orderPhase.value === 'P' && firstP !== Infinity && arrivalP && diffTime.value) {
    const diffStartTime = differenceInMilliseconds(new Date(arrivalP), new Date(firstP))
    return subMinutes(addMilliseconds(firstP, diffStartTime), diffTime.value / 3)
  }

  if (orderPhase.value === 'S' && firstS !== Infinity && arrivalS && diffTime.value) {
    const diffStartTime = differenceInMilliseconds(new Date(arrivalS), new Date(firstS))
    return subMinutes(addMilliseconds(firstS, diffStartTime), diffTime.value / 3)
  }

  return startTime.value!
}

watch([container, startTime, endTime], ([newContainer, newStartTime, newEndTime]) => {
  if (newContainer && newStartTime && newEndTime) {
    const newWidth = newContainer.clientWidth
    width.value = newWidth
    xScale.value = d3.scaleUtc().domain([newStartTime.getTime(), newEndTime.getTime()]).range([0, newWidth])
  }
})

watch(
  [arrivals, pickerStore.events[event._id]],
  ([newArrivals, updatedPicker]) => {
    if (newArrivals.length > 0) {
      const allTimestamps = newArrivals.map((arrival) => new Date(arrival.timestamp).getTime())
      const max = Math.max(...allTimestamps)
      const min = Math.min(...allTimestamps)

      startTime.value = subMinutes(new Date(min), 3)
      endTime.value = addMinutes(new Date(max), 3)
      diffTime.value = differenceInMinutes(endTime.value, startTime.value)

      arrivalByPickId.value = newArrivals.reduce<Record<PickId, StationAndArrival>>((curr, arrival) => {
        const pickId = arrival.pick_details?._id
        const isP = arrival.phase_type === 'P'

        if (!pickId) {
          return curr
        }

        if (!curr[pickId]) {
          curr[pickId] = {
            station: arrival.station_details,
            arrivals: {},
            updatedArrivals: {
              ...updatedPicker?.[pickId]
            }
          }
        }

        if (isP) {
          curr[pickId].arrivals['p'] = arrival
        } else {
          curr[pickId].arrivals['s'] = arrival
        }

        return curr
      }, {})
    }
  },
  { immediate: true }
)

watch(
  arrivalByPickId,
  (newArrivalByPickId) => {
    if (!selectedArrivalByPickId.value) {
      const keys = Object.keys(newArrivalByPickId)
      if (keys.length > 0) {
        selectedArrivalByPickId.value = newArrivalByPickId[keys[0]]
        selectedPickId.value = keys[0]
      }
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="flex flex-col gap-4 h-full">
    <PickingFilter
      v-model:phase="selectedPhase"
      :order-phase="orderPhase"
      @confirm="onConfirm()"
      @close="goBack()"
      @change-order-phase="(newPhase) => (orderPhase = newPhase)" />

    <div ref="container" class="border-t flex-1 h-full">
      <div v-if="!!width && !!xScale && startTime && endTime && diffTime" class="w-full">
        <div v-if="selectedArrivalByPickId && !!selectedStation" class="w-full">
          <ArrivalPickerWaveformItem
            :width="width"
            :x-scale="xScale"
            :station="selectedStation"
            :origin-time="originTime"
            :start-time="startTime"
            :end-time="endTime"
            :arrivals="selectedArrivalByPickId.arrivals"
            :updated-arrivals="selectedArrivalByPickId.updatedArrivals"
            @change-phase="onChangePhase" />
        </div>

        <div class="w-full max-h-[280px] overflow-y-auto">
          <PickingArrivalWaveformItem
            v-for="pickId in Object.keys(arrivalByPickId)"
            :key="pickId"
            :selected="selectedPickId === pickId"
            :width="width"
            :origin-time="originTime"
            :start-time="getStartTimeByPhase(arrivalByPickId[pickId])"
            :end-time="addMinutes(getStartTimeByPhase(arrivalByPickId[pickId]), diffTime)"
            :station="arrivalByPickId[pickId].station"
            :arrivals="joinPSArrival(arrivalByPickId[pickId].arrivals)"
            :updated-arrivals="joinPSArrival(arrivalByPickId[pickId].updatedArrivals)"
            @select-station="onSelectStation(pickId)" />
        </div>
        <!-- <TimestampAxis :width="width" :start-time="startTime.getTime()" :end-time="endTime.getTime()" /> -->
      </div>
    </div>
  </div>
</template>
