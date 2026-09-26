<script setup lang="ts">
import { Station } from '@src/types/station'
import { computed, defineEmits, defineProps, ref } from 'vue'

defineEmits<{
  (e: 'close'): void
  (e: 'select-channel', station: Station): void
}>()

const { stations } = defineProps<{
  stations: Station[]
}>()

const keyword = ref('')

const sortedStations = computed(() => [...stations].sort((a, b) => (a.name < b.name ? -1 : 1)))
const filteredStations = computed(() => {
  if (!keyword.value) {
    return sortedStations.value
  }
  return sortedStations.value.filter((station) => {
    const q = keyword.value.toLowerCase().trim()
    return station.code.toLowerCase().includes(q) || station.name.toLowerCase().includes(q)
  })
})
</script>

<template>
  <div class="drawer z-[9999]">
    <input checked type="checkbox" class="drawer-toggle" />
    <div class="drawer-side">
      <label aria-label="close sidebar" class="drawer-overlay" @click="$emit('close')" />
      <div class="w-full max-w-sm h-full bg-base-100 flex flex-col">
        <div class="p-2 bg-white/5 text-white font-medium">
          <div class="flex justify-between items-center">
            <div>List Stations</div>
            <button class="btn btn-xs btn-error" @click="$emit('close')">
              <v-icon name="md-close" />
            </button>
          </div>
        </div>

        <label class="input input-sm rounded-none flex items-center gap-2">
          <input v-model="keyword" class="grow" placeholder="Search station..." />
          <v-icon name="fa-search" :scale="0.8" />
        </label>

        <div class="flex-1 overflow-y-auto">
          <table class="table table-sm">
            <thead class="bg-slate-700 sticky top-0">
              <tr>
                <th>Code</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="station in filteredStations"
                :id="`${station.network}-${station.code}`"
                :key="station._id"
                class="cursor-pointer hover:bg-white/5"
                @click="$emit('select-channel', station)">
                <td>{{ station.code }}</td>
                <td>{{ station.name }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
