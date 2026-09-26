<script setup lang="ts">
import { EarthQuakeEvent } from '@src/types/event'
import { Magnitude } from '@src/types/magnitude'
import { computed, ref, watch } from 'vue'

import { MagnitudeDetail } from '../magnitude-detail'
import { MagnitudeList } from '../magnitude-list'

const { event } = defineProps<{
  event: EarthQuakeEvent
}>()

const selectedMagnitudeIndex = ref('')

const { magnitudes } = event
const magnitudeList = computed(() =>
  magnitudes.reduce(
    (prev, magnitude) => {
      if (!prev[magnitude.type]) {
        prev[magnitude.type] = [magnitude]
      } else {
        prev[magnitude.type].push(magnitude)
      }
      return prev
    },
    {} as Record<string, Magnitude[]>
  )
)
const magnitudeTypes = computed(() => Object.keys(magnitudeList.value))
const selectedMagnitudes = computed(() => magnitudeList.value[selectedMagnitudeIndex.value])

watch(
  magnitudeTypes,
  (newMagnitudeTypes) => {
    if (newMagnitudeTypes.length > 0) {
      selectedMagnitudeIndex.value = newMagnitudeTypes[0]
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex">
      <div role="tablist" class="tabs tabs-boxed">
        <button
          v-for="magnitudeType in magnitudeTypes"
          :key="magnitudeType"
          role="tab"
          :class="{
            tab: true,
            'tab-active': magnitudeType === selectedMagnitudeIndex
          }"
          @click="selectedMagnitudeIndex = magnitudeType">
          {{ magnitudeType }}
        </button>
      </div>
    </div>

    <MagnitudeDetail v-if="selectedMagnitudes.length > 0" :event="event" :magnitudes="selectedMagnitudes" />

    <MagnitudeList :event="event" :magnitudes="selectedMagnitudes" />
  </div>
</template>
