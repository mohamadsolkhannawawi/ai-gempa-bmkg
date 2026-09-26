<script setup lang="ts">
import { AdminLayout } from './components/admin-layout'
import { FullScreenLoading } from './components/full-screen-loading'
import { LoginPage } from './domain/auth/login-page'
import useGetProfile from './hooks/use-get-profile'

const { data: profile, isLoading } = useGetProfile()

window.socketData = {}
</script>

<template>
  <div class="w-full h-dvh">
    <FullScreenLoading v-if="isLoading" />
    <LoginPage v-else-if="!profile" />
    <AdminLayout v-else>
      <RouterView />
    </AdminLayout>
  </div>
</template>
