<script setup lang="ts">
import useGetProfile from '@src/hooks/use-get-profile'
import Cookies from 'js-cookie'

const { data: profile } = useGetProfile()

const logout = () => {
  Cookies.remove('access_token')
  location.reload()
}
</script>

<template>
  <div class="dropdown dropdown-end z-[9999]">
    <button tabIndex="0" class="avatar placeholder btn btn-circle btn-ghost">
      <div class="bg-primary text-neutral-content rounded-full w-8">
        <span class="text-xs">{{ profile?.username?.[0].toUpperCase() }}</span>
      </div>
    </button>
    <ul tabIndex="0" class="menu menu-sm dropdown-content mt-3 p-2 shadow bg-base-100 rounded-box w-52">
      <li>
        <a class="text-red-400" @click="logout">Logout</a>
      </li>
    </ul>
  </div>
</template>
