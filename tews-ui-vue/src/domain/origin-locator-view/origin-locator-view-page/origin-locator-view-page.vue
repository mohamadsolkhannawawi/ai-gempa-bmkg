<script setup lang="ts">
import { getEventDetailAPI } from '@src/api-service/event'
import { FullScreenLoading } from '@src/components/full-screen-loading'
import { PickingPage } from '@src/domain/picking/picking-page'
import { EarthQuakeEvent } from '@src/types/event'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { EventSummary } from '../event-summary'
import { EventTab } from '../event-tab'
import { LocationDetail } from '../location-detail'
import { MagnitudeTab } from '../magnitude-tab'
import { TabList } from '../tab-list'

const route = useRoute()

const id = computed(() => route.params.id as string)
const selectedTab = computed(() => route.params.tab as string)
const data = ref<EarthQuakeEvent | null>(null)
const isLoading = ref(false)

watch(
  id,
  (newId) => {
    if (newId) {
      isLoading.value = true
      getEventDetailAPI(newId).then((response) => {
        data.value = response
        isLoading.value = false
      })
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="flex flex-1 h-full max-md:flex-col overflow-y-auto md:overflow-hidden">
    <div class="w-[300px] p-4 border-r max-md:w-full max-md:border-none max-md:hidden">
      <EventSummary v-if="!isLoading && !!data" :event="data" />
    </div>
    <div class="flex flex-col p-4 gap-4 flex-1 w-full h-full md:overflow-y-auto">
      <div v-if="selectedTab !== 'picking'" class="flex">
        <TabList :id="id" :selected-tab="selectedTab" />
      </div>

      <LocationDetail v-if="!isLoading && selectedTab === 'location' && !!data" :event="data" />
      <MagnitudeTab v-if="!isLoading && selectedTab === 'magnitude' && !!data" :event="data" />
      <PickingPage v-if="!isLoading && selectedTab === 'picking' && !!data" :event="data" />
      <EventTab v-if="selectedTab === 'events'" />
      <FullScreenLoading v-if="isLoading" />
    </div>
  </div>
</template>
