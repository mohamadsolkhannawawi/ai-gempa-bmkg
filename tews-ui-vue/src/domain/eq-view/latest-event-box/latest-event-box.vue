<script setup lang="ts">
import { EarthQuakeEvent } from '@src/types/event'
import { formatMagnitude, getDefaultMagnitude, newISODate, timeAgo } from '@src/utils/string'

const { event } = defineProps<{
  event: EarthQuakeEvent
}>()

defineEmits<{
  (e: 'click'): void
}>()

const magnitude = getDefaultMagnitude(event.magnitudes)
</script>

<template>
  <div class="bg-white/50 w-80 backdrop-blur-lg rounded-md shadow-sm text-sm text-black max-md:hidden">
    <div class="flex justify-between p-2 font-semibold border-b border-slate-400/40">
      <span>Latest Event</span>
      <button class="link text-xs" @click="$emit('click')">Lihat</button>
    </div>
    <div class="flex items-stretch">
      <div class="p-2 min-w-20 w-20 h-20 flex flex-col items-center justify-center font-semibold bg-black/10 text-3xl">
        {{ formatMagnitude(magnitude?.value ?? 0) }}
      </div>
      <div class="p-2 flex flex-col justify-evenly flex-1 text-lg">
        <div>{{ event.sub_region }}, {{ event.region }}</div>
        <div class="font-extralight text-slate-900 text-sm">
          {{ timeAgo(newISODate(event.cluster_detail[0]?.origin_time)) }}
        </div>
      </div>
    </div>
  </div>
</template>
