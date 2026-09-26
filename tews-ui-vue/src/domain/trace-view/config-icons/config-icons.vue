<template>
  <div class="absolute top-[50%] left-1 flex gap-1" :style="{ transform: 'translateY(-50%)' }">
    <button class="btn btn-square btn-primary btn-xs" @click="emit('open-map')">
      <v-icon name="fa-map" scale="0.8" />
    </button>

    <button class="btn btn-square btn-primary btn-xs" @click="emit('open-settings')">
      <v-icon name="md-settings" scale="0.8" />
    </button>
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits<{
  (e: 'open-map'): void
  (e: 'open-list'): void
  (e: 'open-settings'): void
}>()
</script>
