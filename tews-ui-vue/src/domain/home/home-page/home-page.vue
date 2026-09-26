<script setup lang="ts">
import { HOMEPAGE_MENUS } from '../constants'
import { MenuBox } from '../menu-box'
</script>

<template>
  <div class="container mx-auto max-w-screen-lg px-4 py-8">
    <div class="grid md:grid-cols-3 gap-4 sm:grid-cols-2">
      <MenuBox v-for="menu in HOMEPAGE_MENUS" :key="menu.url" :menu="menu" />
    </div>
  </div>
</template>
