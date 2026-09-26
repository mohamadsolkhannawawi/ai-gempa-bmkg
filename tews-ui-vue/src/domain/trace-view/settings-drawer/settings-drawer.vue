<script setup lang="ts">
const NO_CHANNEL_OPTIONS = [5, 10, 15, 20, 30, 40, 50]
const FILTER_CONFIG_OPTIONS = [
  {
    low: 0.7,
    high: 2
  },
  {
    low: 1,
    high: 3
  },
  {
    low: 2,
    high: 4
  },
  {
    low: 4,
    high: 8
  }
]

interface FilterConfig {
  low: number
  high: number
}

defineProps<{
  maxChannels: number
  open: boolean
  filterConfig?: FilterConfig
}>()

const emit = defineEmits<{
  (e: 'change-max-channels', value: number): void
  (e: 'change-filter-config', filterConfig?: FilterConfig): void
  (e: 'close'): void
}>()

const onChange = (event) => {
  emit('change-max-channels', event.target.value)
}
</script>

<template>
  <div class="drawer z-10">
    <input id="my-drawer" type="checkbox" class="drawer-toggle" :checked="open" />
    <div class="drawer-side">
      <label aria-label="close sidebar" class="drawer-overlay" @click="emit('close')" />

      <ul class="menu w-80 min-h-full bg-base-100 text-base-content p-0">
        <div class="bg-base-200 p-2 px-4 text-lg font-semibold">Display</div>
        <div class="px-4 flex flex-col gap-4">
          <label class="form-control w-full max-w-xs">
            <div class="label">
              <span class="label-text">Number of channels displayed</span>
            </div>
            <select class="select select-bordered" :value="maxChannels" @change="onChange($event)">
              <option v-for="option in NO_CHANNEL_OPTIONS" :key="option">
                {{ option }}
              </option>
            </select>
          </label>

          <label class="form-control w-full max-w-xs">
            <div class="label">
              <span class="label-text">Filter</span>
            </div>
            <div
              v-for="(option, index) in FILTER_CONFIG_OPTIONS"
              :key="index"
              class="form-control"
              @click="$emit('change-filter-config', option)">
              <label class="label cursor-pointer">
                <span class="label-text">{{ option.low }}Hz - {{ option.high }}Hz</span>
                <input
                  type="radio"
                  name="filter"
                  class="radio checked:bg-blue-500"
                  :checked="filterConfig?.low === option.low" />
              </label>
            </div>
            <div class="form-control" @click="$emit('change-filter-config')">
              <label class="label cursor-pointer">
                <span class="label-text">Default</span>
                <input type="radio" name="filter" class="radio checked:bg-blue-500" :checked="!filterConfig" />
              </label>
            </div>
          </label>
        </div>
      </ul>
    </div>
  </div>
</template>
