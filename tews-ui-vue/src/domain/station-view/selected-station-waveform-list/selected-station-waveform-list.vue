<script setup lang="ts">
import { SOCKET_IO_BASE_URL } from '@src/constants/env'
import useArrivalSocket from '@src/hooks/use-arrival-socket'
import { Station } from '@src/types/station'
import { getChannelFullName } from '@src/utils/station'
import * as d3 from 'd3'
import { addMinutes, subMinutes } from 'date-fns'
import { io } from 'socket.io-client'
import { defineProps, onMounted, onUnmounted, ref, watch } from 'vue'

import { StationWaveItem } from '../../trace-view/station-wave-item'

const { station } = defineProps<{
  station: Station
}>()

const socket = io(SOCKET_IO_BASE_URL, {
  transports: ['websocket'],
  autoConnect: true
})

useArrivalSocket()

const CHANNEL_NAME_WIDTH = 50

const isConnected = ref(false)
const width = ref(100)
const endDate = ref(new Date())
const startDate = ref(subMinutes(endDate.value, 30))
const interval = ref<number | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const traceViewContainer = ref<HTMLDivElement | null>(null)
const xScale = ref(d3.scaleUtc().domain([startDate.value.getTime(), endDate.value.getTime()]).range([0, width.value]))

const channelNames = station.channel.map((channel) => getChannelFullName(station, channel))

socket.on('connect_error', () => {
  isConnected.value = false
})

socket.on('connect', () => {
  isConnected.value = true
})

const startInterval = () => {
  interval.value = setInterval(() => {
    const newEndDate = new Date()
    const newStartDate = subMinutes(newEndDate, 30)
    xScale.value = d3.scaleUtc().domain([newStartDate.getTime(), newEndDate.getTime()]).range([0, width.value])
    endDate.value = newEndDate
    startDate.value = newStartDate
  }, 2000)
}

const onVisibilityChange = () => {
  if (document.hidden && interval.value) {
    clearInterval(interval.value)
    interval.value = null
  } else if (!document.hidden && !interval.value) {
    startInterval()
  }
}

const onResize = () => {
  width.value = window.innerWidth
}

onMounted(() => {
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('resize', onResize)
  startInterval()
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('resize', onResize)
  if (interval.value) {
    clearInterval(interval.value)
    interval.value = null
  }
  socket.disconnect()
})

watch(containerRef, (newRef) => {
  if (newRef) {
    const newWidth = newRef.clientWidth - CHANNEL_NAME_WIDTH
    width.value = newWidth
    xScale.value = d3
      .scaleUtc()
      .domain([subMinutes(startDate.value, 0).getTime(), addMinutes(endDate.value, 30).getTime()])
      .range([0, newWidth])
  }
})
</script>

<template>
  <div ref="containerRef">
    <div v-if="!isConnected">Connecting...</div>
    <div v-else class="flex">
      <div class="border-r" :style="{ width: `${CHANNEL_NAME_WIDTH}px`, minWidth: `${CHANNEL_NAME_WIDTH}px` }">
        <div
          v-for="channelName in station.channel"
          :key="channelName"
          :style="{ height: '100px' }"
          class="flex flex-col items-center justify-center py-1 border-b border-b-white/5">
          {{ channelName }}
        </div>
      </div>
      <div ref="traceViewContainer" class="overflow-x-hidden">
        <StationWaveItem
          v-for="channelName in channelNames"
          :key="channelName"
          :socket="socket"
          :channel="{
            channelName,
            stationId: station._id
          }"
          :height="100"
          :width="width"
          :x-scale="xScale"
          :start-time="startDate.getTime()"
          :end-time="endDate.getTime()" />
      </div>
    </div>
  </div>
</template>
