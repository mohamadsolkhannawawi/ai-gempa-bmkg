<script setup lang="ts">
import { defineProps } from 'vue'
import { RouterLink } from 'vue-router'

import { HOMEPAGE_MENUS } from '../constants'

defineProps<{
  menu: (typeof HOMEPAGE_MENUS)[number]
}>()
</script>

<template>
  <div class="card card-compact max-md:card-side w-full bg-base-100 shadow-xl border border-white/10">
    <figure class="max-md:w-[150px] bg-base-200">
      <img :src="menu.image" :alt="menu.label" class="max-md:h-full max-md:w-full max-md:object-contain" />
    </figure>
    <div class="card-body max-md:flex-1">
      <h2 class="card-title">{{ menu.label }}</h2>
      <p>{{ menu.description }}</p>
      <RouterLink :to="menu.url" class="btn btn-sm btn-primary mt-4"> Open </RouterLink>
    </div>
  </div>
</template>
