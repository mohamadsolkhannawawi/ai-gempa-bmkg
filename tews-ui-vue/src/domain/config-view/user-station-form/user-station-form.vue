<script setup lang="ts">
import { getStationListAPI } from '@src/api-service/station'
import { GetStationListQuery } from '@src/api-service/station/types'
import { Input } from '@src/components/input/input'
import { Station } from '@src/types/station'
import { useDebounceFn, useInfiniteScroll } from '@vueuse/core'
import { ref, watch } from 'vue'
import { onMounted } from 'vue'

const emit = defineEmits<{
  (e: 'onCancel', value: null): void
  (e: 'onSubmit', value: string[]): void
}>()

const props = defineProps<{
  isLoading: boolean
  userStation?: string[]
}>()

const stationWrapperRef = ref<HTMLElement | null>(null)
const searchQuery = ref('')
const fetchQuery = ref<GetStationListQuery>({ page: 1, limit: 10 })
const userDataStations = ref<string[]>([''])
const availableStations = ref<Station[] | []>([])
const totalData = ref(0)

useInfiniteScroll(
  stationWrapperRef,
  () => {
    onLoadMore()
  },
  { distance: 10 }
)

const debouncedSearch = useDebounceFn(() => {
  fetchStations()
}, 500)

watch(
  () => props.userStation,
  (newValue) => {
    userDataStations.value = newValue as string[]
  }
)

watch(
  () => searchQuery.value,
  (newValue) => {
    console
    availableStations.value = []
    fetchQuery.value = { ...fetchQuery.value, page: 1, q: newValue }
    debouncedSearch()
  }
)

onMounted(() => {
  fetchStations()
})

function fetchStations() {
  const isRealAPI = false
  getStationListAPI(isRealAPI, fetchQuery.value).then(({ data, total }) => {
    totalData.value = total as number
    data.forEach((item: Station) => availableStations.value.push(item as never))
  })
}

function onLoadMore() {
  if (availableStations.value.length < totalData.value) {
    fetchQuery.value = { ...fetchQuery.value, page: fetchQuery.value.page + 1 }
    fetchStations()
  }
}

function onToggleChange(stationId: string) {
  const isExistOnList = userDataStations.value.find((id) => id === stationId)

  if (isExistOnList) {
    userDataStations.value = userDataStations.value.filter((id) => id !== stationId)
  } else {
    userDataStations.value.push(stationId)
  }
}

function onSubmitForm() {
  emit('onSubmit', userDataStations.value)
}
</script>
<template>
  <div class="flex flex-col gap-2">
    <h3 class="text-xl font-bold mb-2">User Station</h3>
    <Input v-model="searchQuery" placeholder="Search a station..." />
    <div class="flex justify-end items-center">
      <button class="btn btn-ghost btn-sm">Enable All</button>
      <span>/</span>
      <button class="btn btn-ghost btn-sm">Disabled All</button>
    </div>
    <div ref="stationWrapperRef" class="flex flex-col gap-2 h-96 overflow-y-scroll">
      <div
        v-for="station in availableStations"
        :key="station._id"
        class="flex justify-between items-center rounded-md bg-[#252E44] p-2">
        <p class="text-white font-semibold text-base">{{ station.code }}</p>
        <input
          type="checkbox"
          class="toggle toggle-info"
          :checked="userDataStations?.includes(station._id)"
          @change="onToggleChange(station.code)" />
      </div>
    </div>
    <p class="mt-2">Selected channels: {{ userDataStations.length }}</p>
    <div class="flex gap-4">
      <button class="btn btn-outline btn-neutral btn-block shrink" @click="emit('onCancel', null)">Cancel</button>
      <button class="btn btn-info btn-block shrink" @click="onSubmitForm">
        <div v-if="isLoading" class="loading loading-spinner" />
        <span v-else>Submit</span>
      </button>
    </div>
  </div>
</template>
