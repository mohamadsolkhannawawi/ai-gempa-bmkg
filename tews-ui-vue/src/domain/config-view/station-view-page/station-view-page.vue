<script setup lang="ts">
import { deleteStationAPI, getStationListAPI, postStationAPI, putStationAPI } from '@src/api-service/station'
import { GetStationListQuery } from '@src/api-service/station/types'
import { Input } from '@src/components/input/input'
import { Pagination } from '@src/components/pagination'
import { AddStationPayload, Station } from '@src/types/station'
import { useDebounceFn } from '@vueuse/core'
import { onMounted, ref, VNodeRef, watch } from 'vue'
import { toast } from 'vue3-toastify'

import { ConfigLayout } from '../config-layout'
import { StationForm } from '../station-form'

const stationFormModalRef = ref<VNodeRef | null>(null)
const stationDeleteModalRef = ref<VNodeRef | null>(null)

const stations = ref<Station[] | []>([])
const stationPayload = ref<AddStationPayload | null>(null)
const fetchQuery = ref<GetStationListQuery>({ page: 1, limit: 10 })
const isDataFetching = ref(false)
const isDeleting = ref(false)
const searchQuery = ref('')

// form
const isFormReset = ref(false)
const isFormLoading = ref(false)
const selectedStation = ref<Station | null>(null)
const stationFormUsage = ref('create')
const stationFormTitle = ref('Add Station')

// pagination
const totalPages = ref(1)
const totalData = ref(1)
const perPage = ref(10)
const currentPage = ref(1)

const debouncedSearch = useDebounceFn(() => {
  fetchStations()
}, 500)

watch(
  () => searchQuery.value,
  (newValue) => {
    fetchQuery.value = { ...fetchQuery.value, page: 1, q: newValue }
    debouncedSearch()
  }
)

onMounted(() => {
  fetchStations()
})

function resetPageProperty() {
  searchQuery.value = ''
  fetchQuery.value = { page: 1, limit: 10 }
  resetPage()
  fetchStations()
}

function fetchStations() {
  stations.value = []
  isDataFetching.value = true
  const useRealAPI = false
  getStationListAPI(useRealAPI, fetchQuery.value).then(({ data, total }) => {
    stations.value = data
    totalData.value = total as number
    totalPages.value = Math.ceil((total as number) / perPage.value)
    isDataFetching.value = false
  })
}

function addStation() {
  isFormLoading.value = true
  postStationAPI(stationPayload.value as AddStationPayload)
    .then(() => {
      isFormReset.value = true
      onStationFormModalClose()
      resetPageProperty()
      toast.success(`Berhasil menambahkan ${stationPayload.value?.name}.`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .catch((e: Error) => {
      toast.error(`Gagal menambahkan ${stationPayload.value?.name}. \n ${e.message}`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .finally(() => {
      isFormLoading.value = false
    })
}

function updateStation() {
  isFormLoading.value = true
  putStationAPI(selectedStation.value?._id as string, stationPayload.value as AddStationPayload)
    .then(() => {
      isFormReset.value = true
      onStationFormModalClose()
      resetPageProperty()
      toast.success(`Berhasil memperbarui ${stationPayload.value?.name}.`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .catch((e: Error) => {
      toast.error(`Gagal memperbarui ${stationPayload.value?.name}. \n ${e.message}`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .finally(() => {
      isFormLoading.value = false
    })
}

function removeStation() {
  isDeleting.value = true
  deleteStationAPI(selectedStation.value?._id as string)
    .then(() => {
      onModalDeleteClose()
      resetPageProperty()
      toast.success(`Berhasil menghapus ${selectedStation.value?.name}.`, {
        autoClose: 3000,
        position: 'top-center'
      })
      selectedStation.value = null
    })
    .catch((e: Error) => {
      toast.error(`Gagal menghapus ${selectedStation.value?.name}. \n ${e.message}`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .finally(() => {
      isDeleting.value = false
    })
}

function resetPage() {
  fetchQuery.value = { page: 1, limit: 10 }
  currentPage.value = 1
}

function onSubmitStationForm(payload: AddStationPayload) {
  isFormReset.value = false
  stationPayload.value = payload

  stationFormUsage.value === 'create' ? addStation() : updateStation()
}

function onDeleteButtonClick(station: Station) {
  isDeleting.value = false
  stationDeleteModalRef.value.showModal()
  selectedStation.value = station
}

function onEditButtonClick(station: Station) {
  selectedStation.value = station
  stationFormTitle.value = 'Edit Station'
  stationFormUsage.value = 'edit'
  stationFormModalRef.value.showModal()
}

function onStationFormModalClose() {
  stationFormModalRef.value.close()
}

function onModalDeleteClose() {
  stationDeleteModalRef.value.close()
}

function onAddStationButtonClick() {
  stationFormUsage.value = 'create'
  stationFormTitle.value = 'Add Station'
  selectedStation.value = null
  stationFormModalRef.value.showModal()
}

function showMore(page: number) {
  currentPage.value = page
  fetchQuery.value = { ...fetchQuery.value, page }
  fetchStations()
}
</script>

<template>
  <ConfigLayout>
    <div class="p-6 w-full">
      <div class="mb-6">
        <h2 class="font-bold mb-4">Station List</h2>
        <div class="flex items-center justify-between gap-4">
          <Input v-model="searchQuery" class="max-w-80" placeholder="Search . . ." />
          <button class="btn btn-primary" @click="onAddStationButtonClick">Add Station</button>
        </div>
      </div>

      <div class="w-full overflow-x-auto">
        <table class="table max-md:table-sm">
          <thead class="bg-[#2B395C] text-white">
            <tr>
              <th class="min-w-[300px]">Name</th>
              <th>Code</th>
              <th>Network</th>
              <th class="min-w-[200px]">Channels</th>
              <th class="min-w-[200px]">Position</th>
              <th>Server</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody v-if="stations.length">
            <tr v-for="station in stations" :key="station._id">
              <td class="truncate max-w-[300px]">{{ station.name }}</td>
              <td>{{ station.code }}</td>
              <td>{{ station.network }}</td>
              <td class="flex gap-2 flex-wrap max-w-80">
                <div
                  v-for="(channel, idx) in station.channel"
                  :key="idx"
                  class="badge badge-success badge-outline rounded-md font-bold">
                  {{ channel }}
                </div>
              </td>
              <td>{{ station.latitude }}, {{ station.longitude }}</td>
              <td class="text-underline">{{ station.server_seedlink }}</td>
              <td class="flex gap-2">
                <button class="btn btn-square btn-sm btn-outline btn-error" @click="onDeleteButtonClick(station)">
                  <v-icon name="fa-regular-trash-alt" />
                </button>
                <button class="btn btn-square btn-sm btn-outline" @click="onEditButtonClick(station)">
                  <v-icon name="hi-pencil-alt" />
                </button>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr v-if="isDataFetching">
              <td colspan="7">
                <div class="flex items-center justify-center gap-2 w-full">
                  <div class="loading loading-spinner" />
                  <div>Loading...</div>
                </div>
              </td>
            </tr>
            <tr v-else>
              <td colspan="7" class="text-center">Data station not found</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mx-auto">
        <Pagination
          class="mt-4"
          :max-visible-buttons="5"
          :total-pages="totalPages"
          :total="totalData"
          :per-page="perPage"
          :current-page="currentPage"
          @pagechanged="showMore" />
      </div>
      <dialog id="station-form-modal" ref="stationFormModalRef" class="modal">
        <div class="modal-box max-w-3xl">
          <StationForm
            :usage="stationFormUsage"
            :station-data="selectedStation"
            :title="stationFormTitle"
            :is-loading="isFormLoading"
            :is-reset="isFormReset"
            @on-cancel="onStationFormModalClose"
            @on-submit="onSubmitStationForm" />
          <div class="modal-action h-0">
            <form method="dialog" class="modal-backdrop">
              <button>close</button>
            </form>
          </div>
        </div>
      </dialog>
      <dialog id="station-form-modal" ref="stationDeleteModalRef" class="modal">
        <div class="modal-box">
          <h3 class="text-2xl font-bold mb-4">Delete Station</h3>
          <p>
            Are you sure to delete station <span class="text-rose-700 font-bold">{{ selectedStation?.name }}</span> ?
          </p>
          <div class="flex gap-4 mt-4">
            <button class="btn btn-outline btn-error btn-block shrink" @click="onModalDeleteClose">Cancel</button>
            <button class="btn btn-error btn-block shrink" @click="removeStation">
              <div v-if="isDeleting" class="loading loading-spinner" />
              <span v-else>Delete</span>
            </button>
          </div>
          <div class="modal-action">
            <form method="dialog" class="modal-backdrop">
              <button>close</button>
            </form>
          </div>
        </div>
      </dialog>
    </div>
  </ConfigLayout>
</template>
