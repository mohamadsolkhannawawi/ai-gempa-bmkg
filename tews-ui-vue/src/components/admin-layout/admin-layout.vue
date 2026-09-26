<script setup lang="ts">
import { AdminNavbar } from '../admin-navbar'
import { AdminBottomMenu } from './admin-bottom-menu'
</script>

<template>
  <div class="w-full flex flex-col h-dvh overflow-hidden">
    <AdminNavbar />
    <div class="flex-1 h-full overflow-y-auto">
      <slot />
    </div>
    <AdminBottomMenu />
  </div>
</template>
