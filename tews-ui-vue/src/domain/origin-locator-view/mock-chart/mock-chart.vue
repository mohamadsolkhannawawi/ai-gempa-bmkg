<script setup lang="ts">
defineProps<{
  tab: string
}>()
</script>

<template>
  <div class="w-full overflow-hidden">
    <div class="p-[50%] relative">
      <div
        class="w-full h-full bg-base-200 absolute top-0 left-0 rounded-xl flex flex-col items-center justify-center text-white/50">
        {{ tab }}
      </div>
    </div>
  </div>
</template>
