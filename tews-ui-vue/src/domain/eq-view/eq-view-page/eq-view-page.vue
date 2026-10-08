<script setup lang="ts">
import { getAllEventListAPI, getEventDetailAPI } from '@src/api-service/event'
import { GetAllEventListQuery } from '@src/api-service/event/types'
import { DateFilter } from '@src/components/date-filter'
import { OLMap } from '@src/components/ol-map'
import { EarthQuakeEvent } from '@src/types/event'
import { createEventStationLine, createMagnitudeFeature, createSelectedEventStationFeatures } from '@src/utils/ol-map'
import { useToggle } from '@vueuse/core'
import { endOfDay, startOfDay, subWeeks } from 'date-fns'
import { Feature, Map, MapBrowserEvent } from 'ol'
import { LineString, Point } from 'ol/geom'
import VectorLayer from 'ol/layer/Vector'
import { fromLonLat } from 'ol/proj'
import VectorSource from 'ol/source/Vector'
import { computed, ref, watch } from 'vue'

import { ConfigIcons } from '../config-icons'
import { DepthMagnitudeInfo } from '../depth-magnitude-info'
import { EventDetailDrawer } from '../event-detail-info'
import { EventListDrawer } from '../event-list-drawer'
import { LatestEventBox } from '../latest-event-box'

const eventSource = new VectorSource()
const eventLayer = new VectorLayer({
  source: eventSource
})

const map = ref<Map | null>(null)
const totalPerPage = ref(1000)
const totalEvents = ref(0)
const page = ref(1)
const dateRange = ref({
  start: startOfDay(subWeeks(new Date(), 1)),
  end: endOfDay(new Date())
})
const startDate = computed(() => dateRange.value.start.toISOString())
const endDate = computed(() => dateRange.value.end.toISOString())
const selectedEvent = ref<EarthQuakeEvent | null>(null)
const data = ref<EarthQuakeEvent[]>([])
const selectedStationsLayer = ref<VectorLayer<Feature<Point>>>()
const selectedLineLayer = ref<VectorLayer<Feature<LineString>>>()
const latestEvent = ref<EarthQuakeEvent | null>(null)

const [isSettingOpen, toggleSettingOpen] = useToggle()
const [isListOpen, toggleListOpen] = useToggle()

const fetchEventList = (newParams: GetAllEventListQuery) => {
  closeEventDetailDrawer()
  getAllEventListAPI(newParams)
    .then((response) => {
      data.value = response.data
      totalEvents.value = response.total

      if (!latestEvent.value && response.data[0]) {
        latestEvent.value = response.data[0]
      }
    })
    .catch((err) => {
      console.error('[EQView] Failed to fetch events:', err)
      data.value = []
      totalEvents.value = 0
    })
}

const params = computed(() => ({
  page: page.value,
  totalPerPage: totalPerPage.value,
  startDate: startDate.value,
  endDate: endDate.value
}))
const eventList = computed(() => data.value ?? [])
const totalPage = computed(() => Math.ceil(totalEvents.value / totalPerPage.value))

const closeEventDetailDrawer = () => {
  selectedEvent.value = null

  if (selectedStationsLayer.value && map.value) {
    map.value.removeLayer(selectedStationsLayer.value)
  }
  if (selectedLineLayer.value && map.value) {
    map.value.removeLayer(selectedLineLayer.value)
  }
}

const onNewEvent = () => {
  const newStartDate = startOfDay(subWeeks(new Date(), 1))
  const newEndDate = endOfDay(new Date())
  const newPage = 1

  dateRange.value = {
    start: newStartDate,
    end: newEndDate
  }
  page.value = newPage
  latestEvent.value = null

  fetchEventList({
    ...params.value,
    startDate: newStartDate.toISOString(),
    endDate: newEndDate.toISOString(),
    page: newPage
  })
}

const onMapCreated = (createdMap: Map) => {
  map.value = createdMap
  createdMap.addLayer(eventLayer)
}

watch([map, eventList], ([newMap, newEventList], [, oldEventList]) => {
  if (!newMap) return

  eventSource.clear(true)

  if (newEventList !== oldEventList) {
    newEventList.forEach((event) => {
      // Prefer Mw, fallback to first available magnitude
      const magnitude = event.magnitudes.find((info) => info.type.toLowerCase() === 'mw')
        ?? event.magnitudes[0]
      if (magnitude) {
        const feature = createMagnitudeFeature(event, magnitude)
        feature.setProperties({ event })
        eventSource.addFeature(feature)
      }
    })
  }
})

const animateToEvent = (event: EarthQuakeEvent) => {
  map.value?.getView().animate({
    center: fromLonLat([event.longitude, event.latitude]),
    duration: 600
  })
}

const renderSelectedEventStations = async (event: EarthQuakeEvent) => {
  if (!map.value) return

  const eventDetail = await getEventDetailAPI(event._id)

  const linesSource = new VectorSource({
    features: createEventStationLine(eventDetail)
  })

  const stationsSource = new VectorSource({
    features: createSelectedEventStationFeatures(eventDetail)
  })

  const linesLayer = new VectorLayer({
    source: linesSource
  })

  const stationsLayer = new VectorLayer({
    source: stationsSource
  })

  selectedStationsLayer.value = stationsLayer
  selectedLineLayer.value = linesLayer

  map.value.addLayer(linesLayer)
  map.value.addLayer(stationsLayer)
}

const selectEvent = (event: EarthQuakeEvent) => {
  closeEventDetailDrawer()

  setTimeout(() => {
    selectedEvent.value = event
    animateToEvent(event)
    renderSelectedEventStations(event)
  }, 100)
}

const onMapClick = (event: MapBrowserEvent<any>) => {
  eventLayer.getFeatures(event.pixel).then((clickedFeatures) => {
    if (!clickedFeatures.length) return

    const event = clickedFeatures[0].get('event') as EarthQuakeEvent | undefined

    if (event) {
      selectEvent(event)
    }
  })
}

watch(
  params,
  (newParams, oldParams) => {
    if (oldParams) {
      if (oldParams?.startDate !== newParams.startDate || oldParams?.endDate !== newParams.endDate) {
        page.value = 1
        fetchEventList({
          ...newParams,
          page: 1
        })
      } else {
        fetchEventList(newParams)
      }
    } else {
      fetchEventList(newParams)
    }
  },
  { immediate: true, deep: true }
)
</script>

<template>
  <div class="w-full h-full relative">
    <OLMap
      :is-settings-open="isSettingOpen"
      @close-settings="toggleSettingOpen"
      @new-event="onNewEvent()"
      @map-created="onMapCreated"
      @map-click="onMapClick" />

    <div class="absolute top-1 right-1 z-[999] max-md:left-0 max-md:right-0">
      <DateFilter v-model:range="dateRange" class="max-md:text-center" />
    </div>

    <div class="absolute bottom-1 left-1 z-[999]">
      <ConfigIcons @open-settings="toggleSettingOpen" @open-list="toggleListOpen()" />
    </div>

    <div v-if="!!latestEvent" class="absolute right-1 top-10">
      <LatestEventBox :event="latestEvent" @click="selectEvent(latestEvent)" />
    </div>
  </div>

  <EventListDrawer
    v-if="isListOpen"
    v-model:start-date="startDate"
    v-model:end-date="endDate"
    :events="eventList"
    :total-page="totalPage"
    :page="page"
    @change-page="(newPage) => (page = newPage)"
    @close="toggleListOpen()">
    <DateFilter v-model:range="dateRange" />
  </EventListDrawer>

  <div class="absolute right-1 bottom-1 z-[999]">
    <DepthMagnitudeInfo />
  </div>

  <div v-if="!!selectedEvent" class="relative z-[9999]">
    <EventDetailDrawer :event="selectedEvent" @close="closeEventDetailDrawer" />
  </div>
</template>
