<script setup lang="ts">
import { OrderPhaseType } from '@src/types/waveform'

defineProps<{
  orderPhase: OrderPhaseType
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'change-order-phase', phase: OrderPhaseType): void
  (e: 'confirm'): void
}>()

const phase = defineModel<string>('phase')
</script>

<template>
  <div class="flex justify-between items-center min-md:items-center gap-4 max-md:flex-col">
    <div class="flex items-center gap-2 max-md:w-full max-md:overflow-x-auto">
      <button
        class="btn btn-xs"
        :class="{
          'btn-active btn-primary': orderPhase === 'OT',
          'btn-ghost': orderPhase !== 'OT'
        }"
        @click="$emit('change-order-phase', 'OT')">
        OT
      </button>
      <button
        class="btn btn-xs"
        :class="{
          'btn-active btn-primary': orderPhase === 'P',
          'btn-ghost': orderPhase !== 'P'
        }"
        @click="$emit('change-order-phase', 'P')">
        P
      </button>
      <button
        class="btn btn-xs"
        :class="{
          'btn-active btn-primary': orderPhase === 'S',
          'btn-ghost': orderPhase !== 'S'
        }"
        @click="$emit('change-order-phase', 'S')">
        S
      </button>

      <select v-model="phase" className="select select-sm select-bordered w-[80px]">
        <option>P</option>
        <option>S</option>
      </select>

      <select className="select select-sm select-bordered w-[100px] select-disabled">
        <option disabled selected>No Filter</option>
      </select>

      <button class="btn btn-xs btn-ghost btn-disabled">Z</button>
      <button class="btn btn-xs btn-ghost btn-disabled">1(N)</button>
      <button class="btn btn-xs btn-ghost btn-disabled">2(E)</button>
    </div>

    <div class="flex min-md:items-center max-md:justify-end gap-2">
      <button class="btn btn-xs btn-success" @click="$emit('confirm')"><v-icon name="io-checkmark" /></button>
      <button class="btn btn-xs btn-error" @click="$emit('close')"><v-icon name="io-close-sharp" /></button>
    </div>
  </div>
</template>
