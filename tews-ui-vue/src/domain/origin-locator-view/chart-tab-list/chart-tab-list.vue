<script setup lang="ts">
import { ref } from 'vue'

import { MockChart } from '../mock-chart'

const tabs = ['Distance', 'Azimuth', 'Travel Time', 'Move Out']

const selectedTab = ref('Distance')
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex overflow-x-auto">
      <div role="tablist" class="tabs tabs-boxed w-[400px]">
        <div
          v-for="tab in tabs"
          :key="tab"
          role="tab"
          :class="{
            tab: true,
            'tab-active': tab === selectedTab
          }"
          @click="selectedTab = tab">
          {{ tab }}
        </div>
      </div>
    </div>

    <MockChart :tab="selectedTab" />
  </div>
</template>
