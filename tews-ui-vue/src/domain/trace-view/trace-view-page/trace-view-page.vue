<script setup lang="ts">
import { FullScreenLoading } from '@src/components/full-screen-loading'
import useArrivalSocket from '@src/hooks/use-arrival-socket'
import useGetProfile from '@src/hooks/use-get-profile'
import useGetStationList from '@src/hooks/use-get-station-list'
import usePickingSocket from '@src/hooks/use-picking-socket'
import useUpdateStationStatus from '@src/hooks/use-update-station-status'
import { Station } from '@src/types/station'
import { useToggle } from '@vueuse/core'
import * as d3 from 'd3'
import { addMinutes, subMinutes } from 'date-fns'
import { io } from 'socket.io-client'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue3-toastify'

import { SOCKET_IO_BASE_URL } from '../../../constants/env'
import { TRACEVIEW_FILTERED_CHANNEL } from '../../../constants/waveform'
import { getChannelByOrder, getChannelFullName } from '../../../utils/station'
import { ConfigIcons } from '../config-icons'
import { SettingsDrawer } from '../settings-drawer'
import { StationWaveItem } from '../station-wave-item'
import { TimestampAxis } from '../timestamp-axis'
import { TraceViewNavigation } from '../trace-view-navigation'

const TIMESTAMP_HEIGHT = 40
const TAB_HEIGHT = 33
const WRAPPER_HEIGHT = window.innerHeight - TAB_HEIGHT - TIMESTAMP_HEIGHT
const CHANNEL_NAME_WIDTH = 0
const MIN_ROW_HEIGHT = 40

const socket = io(SOCKET_IO_BASE_URL, {
  transports: ['websocket'],
  autoConnect: true,
  reconnectionDelayMax: 2000
})

usePickingSocket()
useArrivalSocket()

const isConnected = ref(false)
const width = ref(window.innerWidth - CHANNEL_NAME_WIDTH)
const endDate = ref(new Date())
const startDate = ref(subMinutes(endDate.value, 30))
const interval = ref<number | null>(null)
const firstTimeout = ref<number | null>(null)
const maxChannels = ref(10)
const filterConfig = ref<undefined | { low: number; high: number }>()
const stationStatus = ref<'ENABLED' | 'DISABLED'>('ENABLED')
const show = ref(true)
const lastScrollY = ref(0)
const heightPerItem = ref(70)
const channelLimit = ref(50)
const traceViewContainer = ref<HTMLDivElement | null>(null)
const xScale = ref(d3.scaleUtc().domain([startDate.value.getTime(), endDate.value.getTime()]).range([0, width.value]))

const router = useRouter()
const { query: routeQuery } = useRoute()
const { data, isLoading } = useGetStationList(true)
const { data: profile, refetch: refetchProfile, isLoading: isProfileLoading } = useGetProfile()
const { mutateAsync: updateStationStatus } = useUpdateStationStatus()
const [isSettingOpen, toggleSettingOpen] = useToggle()
const page = ref(Number(routeQuery['page'] ?? '1'))

const stations = computed(() => data?.value?.data ?? [])
const disabledStationIds = computed(() => profile.value?.disable_stations ?? [])
const userStations = computed(() => {
  console.log("stations.value.stations", stations.value.stations)
  if (!profile.value) return []
  return stations.value.stations.filter((station) => {
    const hasFiltededChannel = TRACEVIEW_FILTERED_CHANNEL.some((filteredChannel) =>
      station.channel.includes(filteredChannel)
    )
    return hasFiltededChannel && profile.value.stations.includes(station._id)
  })
})

const enabledStations = computed(() =>
  userStations.value.filter((station) => !disabledStationIds.value.includes(station._id))
)

const disabledStations = computed(() =>
  userStations.value.filter((station) => disabledStationIds.value.includes(station._id))
)

const selectedStations = computed(() =>
  stationStatus.value === 'ENABLED' ? [...enabledStations.value] : disabledStations.value
)

const slicedStations = computed(() =>
  selectedStations.value.slice((page.value - 1) * channelLimit.value, page.value * channelLimit.value)
)

const totalPage = computed(() => Math.ceil(selectedStations.value.length / channelLimit.value))

socket.on('connect_error', () => {
  isConnected.value = false
})

socket.on('disconnect', (reason) => {
  console.error('socket disconnected!', { reason })
})

socket.on('connect', () => {
  isConnected.value = true
  console.log('koneksi socket trace-view tersambung!')
})

const updateToRedraw = () => {
  const newEndDate = new Date()
  const newStartDate = subMinutes(newEndDate, 30)
  xScale.value = d3.scaleUtc().domain([newStartDate.getTime(), newEndDate.getTime()]).range([0, width.value])
  endDate.value = newEndDate
  startDate.value = newStartDate
}

const startInterval = () => {
  interval.value = setInterval(() => {
    updateToRedraw()
  }, 4000)
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
  const newWidth = window.innerWidth - CHANNEL_NAME_WIDTH

  width.value = newWidth
  xScale.value = d3
    .scaleUtc()
    .domain([startDate.value.getTime(), addMinutes(endDate.value, 30).getTime()])
    .range([0, newWidth])
}

onMounted(() => {
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('resize', onResize)
  startInterval()

  firstTimeout.value = setTimeout(() => {
    updateToRedraw()
  }, 2_000)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('resize', onResize)
  if (interval.value) {
    clearInterval(interval.value)
    interval.value = null
  }
  if (firstTimeout.value) {
    clearTimeout(firstTimeout.value)
    firstTimeout.value = null
  }
  socket.disconnect()
})

const getChannel = (station: Station) => {
  const selectedChannel = getChannelByOrder(station, TRACEVIEW_FILTERED_CHANNEL)

  return {
    channelName: getChannelFullName(station, selectedChannel!),
    stationId: station._id
  }
}

const changeStationStatus = (status: typeof stationStatus.value) => {
  page.value = 1
  stationStatus.value = status
  lastScrollY.value = 0
}

const toggleStation = (station: Station, enabled: boolean) => {
  const container = document.querySelector('#trace-view-container')
  if (container) {
    lastScrollY.value = container.scrollTop
  }

  updateStationStatus(
    {
      stationId: station._id,
      enabled
    },
    {
      onSuccess() {
        refetchProfile()
      }
    }
  )
}

const navigateToStationView = () => {
  router.push('/station-view')
}

watch([maxChannels], ([newMaxChannels]) => {
  let rowHeight = WRAPPER_HEIGHT / newMaxChannels
  if (rowHeight < MIN_ROW_HEIGHT) {
    toast.info(
      `Sorry, the screen is too small to display all ${newMaxChannels} channels in one screen. The system will adjust the height automatically.`
    )
    rowHeight = MIN_ROW_HEIGHT
  }
  heightPerItem.value = rowHeight
})

const nextPage = () => {
  router.replace(`/trace-view?page=${page.value + 1}`)
  page.value += 1
}

const prevPage = () => {
  router.replace(`/trace-view?page=${page.value - 1}`)
  page.value -= 1
}
</script>

<template>
  <FullScreenLoading v-if="isLoading || isProfileLoading || !isConnected" />
  <div v-else class="flex flex-col h-full overflow-hidden border-t border-t-white/10">
    <TraceViewNavigation
      :status="stationStatus"
      :total-enabled="enabledStations.length"
      :total-disabled="disabledStations.length"
      :page="page"
      :total-page="totalPage"
      :limit="channelLimit"
      @change-status="changeStationStatus"
      @change-limit="(newLimit) => (channelLimit = newLimit)"
      @next-page="nextPage"
      @prev-page="prevPage" />
    <div class="flex-1 w-full h-full overflow-y-auto">
      <div class="flex">
        <div v-if="show" id="trace-view-container" ref="traceViewContainer" class="h-full flex-1 overflow-x-hidden">
          <StationWaveItem
            v-for="station in slicedStations"
            :key="station._id"
            :enabled="stationStatus === 'ENABLED'"
            :socket="socket"
            :channel="getChannel(station)"
            :height="heightPerItem"
            :width="width"
            :start-time="startDate.getTime()"
            :end-time="endDate.getTime()"
            :show-toggle="true"
            :x-scale="xScale"
            :filter-config="filterConfig"
            @toggle="toggleStation(station, stationStatus !== 'ENABLED')" />
        </div>
      </div>
    </div>

    <div className="relative w-full overflow-hidden">
      <div :style="{ transform: `translateX(${CHANNEL_NAME_WIDTH}px)` }">
        <TimestampAxis :width="width" :start-time="startDate.getTime()" :end-time="endDate.getTime()" />
      </div>
      <ConfigIcons @open-map="navigateToStationView" @open-settings="toggleSettingOpen" />
    </div>
  </div>
  <SettingsDrawer
    v-if="isSettingOpen"
    :open="isSettingOpen"
    :max-channels="maxChannels"
    :filter-config="filterConfig"
    @close="toggleSettingOpen"
    @change-filter-config="(newValue) => (filterConfig = newValue)"
    @change-max-channels="(newValue) => (maxChannels = newValue)" />
</template>
