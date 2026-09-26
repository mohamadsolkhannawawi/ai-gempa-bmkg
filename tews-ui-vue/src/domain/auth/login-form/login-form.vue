<script setup lang="ts">
import { Input } from '@src/components/input/input'
import { computed, ref } from 'vue'

defineEmits<{
  (
    e: 'submit',
    value: {
      username: string
      password: string
    }
  ): void
}>()

defineProps<{
  isLoading?: boolean
}>()

const username = ref('')
const password = ref('')

const isValid = computed(() => username.value.length > 0 && password.value.length > 0)
</script>

<template>
  <form class="flex flex-col gap-6" @submit.prevent="$emit('submit', { username, password })">
    <div class="text-xl font-bold">Masuk</div>

    <Input v-model="username" label="Username" placeholder="Masukkan username..." />

    <Input v-model="password" type="password" label="Password" placeholder="••••••••" />

    <button
      type="submit"
      class="btn btn-primary"
      :class="{
        'btn-disabled': !isValid || isLoading
      }">
      Login
    </button>
  </form>
</template>
