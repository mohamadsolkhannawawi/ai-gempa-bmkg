<script setup lang="ts">
defineProps<{
  items: {
    label: string
    value?: string | number
  }[]
}>()
</script>

<template>
  <table className="mx-auto table-fixed">
    <tr v-for="item in items" :key="item.label">
      <td className="text-right pr-4 w-1/2">{{ item.label }}</td>
      <td className="w-1/2">{{ item.value }}</td>
    </tr>
  </table>
</template>
