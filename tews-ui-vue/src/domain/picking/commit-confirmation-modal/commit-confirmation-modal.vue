<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  isOpen: boolean
  totalArrivals: number
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'confirm'): void
}>()

const commitConfirmationModal = ref<HTMLDialogElement | null>(null)

watch(
  [commitConfirmationModal, () => props.isOpen],
  ([confirmationModal, isOpen]) => {
    if (confirmationModal) {
      if (isOpen) {
        confirmationModal.showModal()
      } else {
        confirmationModal.close()
      }
    }
  },
  { immediate: true }
)
</script>

<template>
  <dialog ref="commitConfirmationModal" className="modal">
    <div className="modal-box">
      <h3 className="font-bold text-lg">Commit Confirmation</h3>
      <p className="pt-4">Are you sure, you want to commit {{ totalArrivals }} arrivals?</p>
      <div className="modal-action">
        <div class="flex gap-2">
          <button className="btn btn-ghost" @click="$emit('close')">Close</button>
          <button className="btn btn-primary" @click="$emit('confirm')">Confirm</button>
        </div>
      </div>
    </div>
  </dialog>
</template>
