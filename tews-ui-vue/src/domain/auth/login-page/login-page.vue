<script setup lang="ts">
import { LoginResponse } from '@src/types/auth'
import api from '@src/utils/api'
import { useMutation } from '@tanstack/vue-query'
import Cookies from 'js-cookie'
import { toast } from 'vue3-toastify'

import { LoginForm, LoginSchema } from '../login-form'

const showLoginError = () => toast.error('Silahkan cek kembali username dan password Anda')

const onLoginSuccess = (data: LoginResponse) => {
  if (!data.status) {
    showLoginError()
    return
  }

  Cookies.set('access_token', data.data.access_token, { expires: 1 })
  location.reload()
}

const { isPending, mutate: login } = useMutation({
  mutationFn: (data: LoginSchema) =>
    api<LoginResponse>({
      method: 'POST',
      url: '/user/login',
      data
    }),
  onSuccess({ data }) {
    if (data) onLoginSuccess(data)
  },
  onError: () => {
    showLoginError()
  }
})
</script>

<template>
  <div class="min-h-full flex flex-col justify-center items-center">
    <div class="max-w-[440px] w-full flex flex-col gap-6 px-4 py-8">
      <div class="flex flex-col gap-4 items-center justify-center">
        <img src="/images/geomecca-logo.png" :width="60" />
        <div class="text-4xl font-extrabold">GEOMECCA</div>
      </div>
      <div class="bg-base-200 border border-white/5 shadow-xl rounded-md p-8">
        <LoginForm :is-loading="isPending" @submit="login" />
      </div>
    </div>
  </div>
</template>
