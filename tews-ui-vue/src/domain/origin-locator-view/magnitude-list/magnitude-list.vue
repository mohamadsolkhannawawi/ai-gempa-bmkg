<script setup lang="ts">
import { Magnitude } from '@src/types/magnitude'

defineProps<{
  magnitudes: Magnitude[]
}>()
</script>

<template>
  <table class="table table-sm">
    <thead class="bg-base-200 sticky top-0">
      <tr>
        <th>Type</th>
        <th class="text-right">Magnitude</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="magnitude in magnitudes" :key="magnitude._id">
        <td>{{ magnitude.type }}</td>
        <td class="text-right">{{ magnitude.value }}</td>
      </tr>
    </tbody>
  </table>
</template>
