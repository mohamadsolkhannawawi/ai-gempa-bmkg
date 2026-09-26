<script setup lang="ts">
import { EventListTable } from '@src/components/event-list-table'
import { EarthQuakeEvent } from '@src/types/event'
import { defineEmits, defineProps } from 'vue'

defineEmits<{
  (e: 'close'): void
  (e: 'change-page', page: number): void
}>()

defineProps<{
  events: EarthQuakeEvent[]
  totalPage: number
  page: number
}>()
</script>

<template>
  <div class="flex flex-col w-full h-full top-0 left-0 fixed z-[9999] bg-base-300">
    <div class="flex items-center justify-between p-3 bg-white/5">
      <div>Events</div>
      <div class="inline-flex items-center gap-2">
        <slot />
        <button class="btn btn-xs btn-error" @click="$emit('close')">
          <v-icon name="md-close" />
        </button>
      </div>
    </div>

    <div class="flex-1 h-full overflow-y-auto">
      <EventListTable :events="events" />
    </div>

    <div class="flex justify-end p-2 bg-white/5">
      <div class="join">
        <button
          v-for="(_, index) in [...new Array(totalPage)]"
          :key="index"
          :class="{
            'join-item btn btn-sm': true,
            'btn-active btn-primary': index + 1 === page
          }"
          @click="$emit('change-page', index + 1)">
          {{ index + 1 }}
        </button>
      </div>
    </div>
  </div>
</template>
