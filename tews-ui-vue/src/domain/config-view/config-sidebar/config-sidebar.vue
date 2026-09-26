<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'

import { CONFIG_MENU } from '../constants'

const route = useRoute()
</script>

<template>
  <ul class="menu">
    <li v-for="menu in CONFIG_MENU" :key="menu.label">
      <RouterLink :to="menu.url" :class="route.name === menu.routeName ? 'active' : ''">
        {{ menu.label }}
      </RouterLink>
    </li>
  </ul>
</template>
