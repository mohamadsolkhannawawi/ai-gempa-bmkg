<script setup lang="ts">
import { NAVBAR_MENUS } from '@src/constants/navbar'
import { RouterLink, useRoute } from 'vue-router'

import { AdminMenu } from './admin-menu'

const route = useRoute()

const filteredMenus = NAVBAR_MENUS.filter((menu) => menu.label !== 'Home')
</script>

<template>
  <div class="navbar bg-base-200">
    <div class="navbar-start">
      <RouterLink to="/" class="btn btn-ghost text-xl"> TEWS </RouterLink>
    </div>
    <div class="navbar-center hidden md:flex">
      <ul class="menu menu-horizontal px-1">
        <li v-for="menu in filteredMenus" :key="menu.path">
          <RouterLink
            :to="menu.path"
            :class="{
              active: menu.path === route.path
            }">
            <v-icon :name="menu.icon" scale="1" />
            <span class="btm-nav-label">{{ menu.label }}</span>
          </RouterLink>
        </li>
      </ul>
    </div>
    <div class="navbar-end">
      <AdminMenu />
    </div>
  </div>
</template>
