<script setup lang="ts">
import { getAllEventListAPI } from '@src/api-service/event'
import { GetAllEventListQuery } from '@src/api-service/event/types'
import { DateFilter } from '@src/components/date-filter'
import { EventListTable } from '@src/components/event-list-table'
import { EarthQuakeEvent } from '@src/types/event'
import { endOfDay, startOfDay, subWeeks } from 'date-fns'
import { computed, ref, watch } from 'vue'

const page = ref(1)
const totalPerPage = ref(1000)
const dateRange = ref({
  start: startOfDay(subWeeks(new Date(), 1)),
  end: endOfDay(new Date())
})
const startDate = computed(() => dateRange.value.start.toISOString())
const endDate = computed(() => dateRange.value.end.toISOString())
const data = ref<EarthQuakeEvent[]>([])

const params = computed(() => ({
  page: page.value,
  totalPerPage: totalPerPage.value,
  startDate: startDate.value,
  endDate: endDate.value
}))
const eventList = computed(() => data.value ?? [])

const fetchEventList = (newParams: GetAllEventListQuery) => {
  getAllEventListAPI(newParams).then((response) => {
    data.value = response.data
  })
}

watch(
  params,
  (newParams) => {
    fetchEventList(newParams)
  },
  { immediate: true, deep: true }
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <DateFilter v-model:range="dateRange" />
    <div class="w-full overflow-x-auto">
      <EventListTable :events="eventList" />
    </div>
  </div>
</template>
