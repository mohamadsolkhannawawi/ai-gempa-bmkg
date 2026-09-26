<script setup lang="ts">
const model = defineModel<string>()

withDefaults(
  defineProps<{
    label?: string
    error?: string
    type?: string
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    disabled: false,
    placeholder: '',
    error: '',
    type: 'text',
    label: ''
  }
)
</script>

<template>
  <label class="form-control w-full">
    <div v-if="!!label" class="label pl-0 font-light pt-0">
      <span class="label-text">{{ label }}</span>
    </div>
    <input
      v-model="model"
      :type="type"
      class="input input-bordered placeholder-white/40"
      :disabled="disabled"
      :placeholder="placeholder" />
    <div v-if="!!error" class="label">
      <span class="label-text-alt text-error">{{ error }}</span>
    </div>
  </label>
</template>
