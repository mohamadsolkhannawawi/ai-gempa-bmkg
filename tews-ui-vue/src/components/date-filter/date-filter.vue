<script setup lang="ts">
import 'v-calendar/style.css'

import { format as formatDate } from 'date-fns'
import { DatePicker } from 'v-calendar'
import { defineModel } from 'vue'

const range = defineModel<{
  start: Date
  end: Date
}>('range')
</script>

<template>
  <div>
    <DatePicker v-model.range="range">
      <template #default="{ togglePopover }">
        <button class="btn btn-sm max-md:btn-xs btn-neutral" @click="togglePopover">
          <v-icon name="fa-calendar" />
          {{ formatDate(range?.start ?? new Date(), 'dd MMM yyyy') }} -
          {{ formatDate(range?.end ?? new Date(), 'dd MMM yyyy') }}
        </button>
      </template>
    </DatePicker>
  </div>
</template>
