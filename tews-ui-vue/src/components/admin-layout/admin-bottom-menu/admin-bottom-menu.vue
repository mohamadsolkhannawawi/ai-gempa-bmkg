<script setup lang="ts">
import { NAVBAR_MENUS } from '@src/constants/navbar'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
</script>

<template>
  <div class="overflow-x-auto hidden max-md:block">
    <div class="btm-nav btm-nav-sm static bg-base-200 min-w-[420px]">
      <button
        v-for="menu in NAVBAR_MENUS"
        :key="menu.path"
        :class="{
          'active text-secondary': route.path === menu.path
        }"
        @click="router.push(menu.path)">
        <v-icon :name="menu.icon" scale="1.1" />
        <span class="btm-nav-label">{{ menu.label }}</span>
      </button>
    </div>
  </div>
</template>
