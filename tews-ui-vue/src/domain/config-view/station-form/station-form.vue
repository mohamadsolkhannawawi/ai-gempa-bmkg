<script setup lang="ts">
import { Input } from '@src/components/input/input'
import { AddStationPayload, Station } from '@src/types/station'
import { ref, watch } from 'vue'

const emit = defineEmits<{
  (e: 'onCancel', value: null): void
  (e: 'onSubmit', value: AddStationPayload): void
}>()

const props = defineProps<{
  usage?: string
  stationData?: Station | null
  title: string
  isLoading: boolean
  isReset: boolean
}>()

const name = ref('')
const code = ref('')
const network = ref('')
const latitude = ref<number | null>(null)
const longitude = ref<number | null>(null)
const elevation = ref<number | null>(null)
const server_seedlink = ref('')
const server_fdsn = ref('')
const channel = ref([''])

function resetForm() {
  name.value = ''
  code.value = ''
  network.value = ''
  latitude.value = null
  longitude.value = null
  elevation.value = null
  server_seedlink.value = ''
  server_fdsn.value = ''
  channel.value = ['']
}

watch(
  () => props.stationData,
  (newValue) => {
    if (newValue) {
      mappedDataToForm(newValue as Station)
    } else {
      resetForm()
    }
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

function mappedDataToForm(station: Station) {
  name.value = station.name
  code.value = station.code
  network.value = station.network
  latitude.value = station.latitude
  longitude.value = station.longitude
  elevation.value = station.elevation
  server_seedlink.value = station.server_seedlink
  server_fdsn.value = station.server_fdsn
  channel.value = station.channel
}

function onSubmitForm() {
  emit('onSubmit', {
    name: name.value,
    code: code.value,
    network: network.value,
    latitude: latitude.value as number,
    longitude: longitude.value as number,
    elevation: elevation.value as number,
    server_seedlink: server_seedlink.value,
    server_fdsn: server_fdsn.value,
    channel: channel.value
  })
}

function addChannel() {
  channel.value.push('')
}

function removeChannel(index: number) {
  channel.value.splice(index, 1)
}
</script>

<template>
  <div>
    <h3 class="text-xl font-bold mb-2">{{ title }}</h3>
    <div class="flex flex-col gap-4">
      <Input v-model="name" label="Name" />
      <Input v-model="code" label="Code" />
      <Input v-model="network" label="Network" />
      <div>
        <div class="label pl-0 font-semibold pt-0">
          <span class="label-text">Channels</span>
        </div>
        <div class="flex flex-col gap-4 mb-4">
          <div v-for="(_, idx) in channel" :key="idx" class="flex gap-4">
            <Input v-model="channel[idx]" />
            <button class="btn btn-outline btn-error btn-square" @click="removeChannel(idx)">
              <v-icon name="fa-regular-trash-alt" />
            </button>
          </div>
        </div>
        <button class="btn btn-block btn-outline btn-info btn-md" @click="addChannel">Add Channel</button>
      </div>
      <div class="grid grid-cols-3 max-md:grid-cols-1 gap-4">
        <Input v-model="latitude" label="Latitude" type="number" />
        <Input v-model="longitude" label="Longitude" type="number" />
        <Input v-model="elevation" label="Elevation" type="number" />
      </div>
      <Input v-model="server_seedlink" label="Server FDSN" />
      <Input v-model="server_fdsn" label="Server Seedlink" />
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
