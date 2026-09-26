<script setup lang="ts">
import { ConfigSidebar } from '../config-sidebar'
</script>

<template>
  <div class="flex h-full overflow-hidden">
    <div class="max-md:hidden h-full bg-base-300 w-72">
      <ConfigSidebar />
    </div>
    <div class="h-full w-full overflow-y-auto">
      <slot />
    </div>
  </div>
</template>
