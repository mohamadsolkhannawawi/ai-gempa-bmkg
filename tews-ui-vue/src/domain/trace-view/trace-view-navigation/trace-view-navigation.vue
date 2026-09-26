<script setup lang="ts">
import { defineEmits, defineProps, ref, watch } from 'vue'

type Status = 'ENABLED' | 'DISABLED'

const props = defineProps<{
  status: Status
  page: number
  limit: number
  totalPage: number
  totalEnabled: number
  totalDisabled: number
}>()

defineEmits<{
  (e: 'change-status', newStatus: Status): void
  (e: 'change-limit', newLimit: number): void
  (e: 'next-page'): void
  (e: 'prev-page'): void
}>()

// const changeLimit = (event: Event) => {
//   const target = event.target as HTMLSelectElement
//   emit('change-limit', Number(target.value))
// }

const { page, totalPage } = props

const isPrevEnabled = ref(page > 1)
const isNextEnabled = ref(page < totalPage)

watch(
  () => props.page,
  (newPage) => {
    isPrevEnabled.value = newPage > 1
    isNextEnabled.value = newPage < totalPage
  }
)
</script>

<template>
  <div class="flex justify-between items-center bg-base-200 border-b">
    <div role="tablist" class="tabs tabs-sm tabs-boxed">
      <a
        role="tab"
        class="tab"
        :class="{
          'tab-active': status === 'ENABLED'
        }"
        @click="$emit('change-status', 'ENABLED')"
        >Enabled ({{ totalEnabled }})</a
      >
      <a
        role="tab"
        class="tab"
        :class="{
          'tab-active': status === 'DISABLED'
        }"
        @click="$emit('change-status', 'DISABLED')"
        >Disabled ({{ totalDisabled }})</a
      >
    </div>

    <div class="flex gap-1 items-center">
      <!-- <select
        className="select select-bordered select-sm"
        :value="limit"
        @change="changeLimit($event)"
      >
        <option disabled selected>Limit</option>
        <option value="5">5</option>
        <option value="50">50</option>
        <option value="100">100</option>
      </select> -->

      <div class="join">
        <button
          :class="{
            'join-item btn btn-primary btn-xs': true,
            'btn-disabled': !isPrevEnabled
          }"
          @click="$emit('prev-page')">
          «
        </button>
        <!-- <button class="join-item btn btn-primary btn-xs btn-outline">Page {{ page }}</button> -->
        <button
          :class="{
            'join-item btn btn-primary btn-xs': true,
            'btn-disabled': !isNextEnabled
          }"
          @click="$emit('next-page')">
          »
        </button>
      </div>
    </div>
  </div>
</template>
