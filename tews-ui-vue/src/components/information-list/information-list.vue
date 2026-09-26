<script setup lang="ts">
defineProps<{
  informations: {
    label: string
    value: string | number
    width?: string
  }[]
}>()
</script>

<template>
  <table class="table table-xs">
    <tr v-for="info in informations" :key="info.label">
      <td class="text-right" :width="info.width">{{ info.label }}</td>
      <td class="truncate text-white">{{ info.value }}</td>
    </tr>
  </table>
</template>
