<script setup lang="ts">
defineEmits<{
  (e: 'open-list'): void
  (e: 'open-settings'): void
}>()
</script>

<template>
  <div class="flex gap-1 items-center">
    <button class="btn btn-square btn-sm" @click="$emit('open-list')">
      <v-icon name="fa-list" />
    </button>

    <button class="btn btn-square btn-sm" @click="$emit('open-settings')">
      <v-icon name="md-settings" />
    </button>
  </div>
</template>
