<script setup lang="ts">
import { EarthQuakeEvent } from '@src/types/event'
import {
  formatDate,
  formatDepth,
  formatLatLon,
  formatMagnitude,
  getDefaultMagnitude,
  getOriginTimeFromEvent,
  newISODate
} from '@src/utils/string'
import { reverse, sortBy } from 'lodash'
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{
  events: EarthQuakeEvent[]
}>()

const sortedEvents = ref<EarthQuakeEvent[]>([])

const router = useRouter()

const onEventClick = (event: EarthQuakeEvent) => {
  router.push(`/origin-locator-view/location/${event._id}`)
}

watch(
  () => props.events,
  (newEvents) => {
    sortedEvents.value = reverse(
      sortBy(newEvents, (event) => newISODate(event.cluster_detail?.[0]?.origin_time).getTime())
    )
  },
  { immediate: true }
)
</script>

<template>
  <table class="table table-sm">
    <thead class="bg-base-200 sticky top-0">
      <tr>
        <th class="min-w-[180px]">Origin Time</th>
        <th>Latitude</th>
        <th>Longitude</th>
        <th>Magnitude</th>
        <th>Depth</th>
        <th>Region</th>
        <th>Country</th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="event in sortedEvents"
        :key="event._id"
        class="cursor-pointer hover:bg-white/5"
        @click="onEventClick(event)">
        <td>{{ formatDate(getOriginTimeFromEvent(event)) }}</td>
        <td>{{ formatLatLon(event.latitude) }}</td>
        <td>{{ formatLatLon(event.longitude) }}</td>
        <td>
          {{ formatMagnitude(getDefaultMagnitude(event.magnitudes)?.value ?? 0) }}
        </td>
        <td>{{ formatDepth(event.depth) }}</td>
        <td>{{ event.region }}</td>
        <td>{{ event.country }}</td>
      </tr>
    </tbody>
  </table>
</template>
