<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  id: string
  selectedTab: string
}>()
</script>

<template>
  <div role="tablist" class="tabs tabs-boxed">
    <RouterLink
      role="tab"
      :to="`/origin-locator-view/location/${id}`"
      :class="{
        tab: true,
        'tab-active': selectedTab === 'location',
        'tab-disabled': !id,
        'pointer-events-none': !id
      }">
      Location
    </RouterLink>
    <RouterLink
      role="tab"
      :to="`/origin-locator-view/magnitude/${id}`"
      :class="{
        tab: true,
        'tab-active': selectedTab === 'magnitude',
        'tab-disabled': !id,
        'pointer-events-none': !id
      }">
      Magnitude
    </RouterLink>
    <RouterLink
      role="tab"
      to="/origin-locator-view/events"
      :class="{
        tab: true,
        'tab-active': selectedTab === 'events'
      }">
      Events
    </RouterLink>
  </div>
</template>
