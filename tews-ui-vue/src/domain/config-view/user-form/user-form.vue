<script setup lang="ts">
import { Input } from '@src/components/input/input'
import { AddUserPayload, User } from '@src/types/user'
import { ref, watch } from 'vue'

const emit = defineEmits<{
  (e: 'onCancel', value: null): void
  (e: 'onSubmit', value: AddUserPayload): void
}>()

const props = defineProps<{
  usage: string
  userData?: User | null
  title: string
  isLoading: boolean
  isReset: boolean
}>()

const username = ref('')
const region = ref('')
const password = ref('')

function resetForm() {
  username.value = ''
  region.value = ''
  password.value = ''
}

watch(
  () => props.userData,
  (newValue) => {
    username.value = newValue?.username as string
    region.value = newValue?.region as string
  }
)

watch(
  () => props.isReset,
  (newValue) => {
    if (newValue) {
      resetForm()
    }
  }
)

function onSubmitForm() {
  emit('onSubmit', {
    username: username.value,
    region: region.value,
    password: password.value
  })
}
</script>

<template>
  <div>
    <h3 class="text-xl font-bold mb-2">{{ title }}</h3>
    <div class="flex flex-col gap-2">
      <Input v-model="username" label="Username" />
      <Input v-model="region" label="Region" />
      <Input v-if="usage !== 'edit'" v-model="password" type="password" label="Password" />
      <div class="flex gap-4 mt-4">
        <button class="btn btn-outline btn-neutral btn-block shrink" @click="emit('onCancel', null)">Cancel</button>
        <button class="btn btn-info btn-block shrink" @click="onSubmitForm">
          <div v-if="isLoading" class="loading loading-spinner" />
          <span v-else>Submit</span>
        </button>
      </div>
    </div>
  </div>
</template>
