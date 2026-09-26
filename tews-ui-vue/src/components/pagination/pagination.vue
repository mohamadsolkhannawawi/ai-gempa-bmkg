<script setup lang="ts">
import { computed, defineEmits, defineProps } from 'vue'

interface IProps {
  maxVisibleButtons?: number
  totalPages: number
  total: number
  perPage: number
  currentPage: number
}

const props = withDefaults(defineProps<IProps>(), {
  maxVisibleButtons: 3
})

const emit = defineEmits<{
  (e: 'pagechanged', value: number): void
}>()

function onClickPreviousPage() {
  emit('pagechanged', props.currentPage - 1)
}

function onClickPage(page: number) {
  emit('pagechanged', page)
}

function onClickNextPage() {
  emit('pagechanged', props.currentPage + 1)
}

function isPageActive(page: number) {
  return props.currentPage === page
}

const startPage = computed(() => {
  if (props.currentPage === 1) {
    return 1
  }

  if (props.currentPage === props.totalPages) {
    return props.totalPages - props.maxVisibleButtons + 1
  }

  return props.currentPage - 1
})

const endPage = computed(() => {
  return Math.min(startPage.value + props.maxVisibleButtons - 1, props.totalPages)
})
const pages = computed(() => {
  const range = []

  for (let i = startPage.value; i <= endPage.value; i += 1) {
    range.push({
      name: i,
      isDisabled: i === props.currentPage
    })
  }

  return range
})

const isInFirstPage = computed(() => {
  return props.currentPage === 1
})

const isInLastPage = computed(() => {
  return props.currentPage === props.totalPages
})
</script>

<template>
  <div class="flex justify-center">
    <div class="join">
      <input
        class="join-item btn btn-square"
        :class="{ 'cursor-not-allowed': isInFirstPage }"
        type="radio"
        name="options"
        aria-label="Prev"
        :disabled="isInFirstPage"
        @click="onClickPreviousPage" />
      <input
        v-for="page in pages"
        :key="page.name"
        class="join-item btn btn-square"
        type="radio"
        name="options"
        :aria-label="page.name.toString()"
        :checked="isPageActive(page.name)"
        @click="onClickPage(page.name)" />
      <input
        class="join-item btn btn-square pr-1"
        type="radio"
        name="options"
        aria-label="Next"
        :disabled="isInLastPage"
        @click="onClickNextPage" />
    </div>
  </div>
</template>
