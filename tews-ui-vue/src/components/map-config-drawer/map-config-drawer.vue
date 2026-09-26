<script setup lang="ts">
import { defineEmits, defineProps } from 'vue'

type SettingName = 'volcanoes' | 'trench' | 'plateBoundaries' | 'pusgen'

const props = defineProps<{
  value: Record<string, boolean>
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'change', name: SettingName, value: boolean): void
}>()

const OPTIONS = [
  {
    label: 'Show Trench',
    name: 'trench'
  },
  {
    label: 'Show Plate Boundaries',
    name: 'plateBoundaries'
  },
  {
    label: 'Show Volcanoes',
    name: 'volcanoes'
  },
  {
    label: 'Show Pusgen',
    name: 'pusgen'
  }
  // {
  //   label: 'Activate Alarm',
  //   name: 'alarm',
  // },
] as const

const onCheckboxClick = (name: SettingName) => {
  emit('change', name, !props.value[name])
}
</script>

<template>
  <div class="drawer z-[9999]">
    <input checked type="checkbox" class="drawer-toggle" />
    <div class="drawer-side">
      <label aria-label="close sidebar" class="drawer-overlay" @click="$emit('close')" />
      <div class="flex flex-col gap-2 p-4 w-80 min-h-full bg-base-100">
        <div v-for="option in OPTIONS" :key="option.name" class="form-control">
          <label class="label cursor-pointer">
            <span class="label-text">{{ option.label }}</span>
            <input
              type="checkbox"
              class="toggle toggle-sm toggle-primary"
              :value="option.name"
              :checked="value[option.name] ?? false"
              @click="onCheckboxClick(option.name)" />
          </label>
        </div>
      </div>
    </div>
  </div>
</template>
