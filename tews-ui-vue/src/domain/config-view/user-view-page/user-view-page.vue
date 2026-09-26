<script setup lang="ts">
import { deleteUserAPI, getUsersAPI, postUserAPI, putUserAPI } from '@src/api-service/users'
import { GetAllUserListQuery } from '@src/api-service/users/types'
import { Input } from '@src/components/input/input'
import { Pagination } from '@src/components/pagination'
import { AddUserPayload, UpdateUserPayload, User } from '@src/types/user'
import { useDebounceFn } from '@vueuse/core'
import { onMounted, ref, VNodeRef, watch } from 'vue'
import { toast } from 'vue3-toastify'

import { ConfigLayout } from '../config-layout'
import { UserForm } from '../user-form'
import { UserStationForm } from '../user-station-form'

const userFormModalRef = ref<VNodeRef | null>(null)
const userDeleteModalRef = ref<VNodeRef | null>(null)
const userStationModalRef = ref<VNodeRef | null>(null)

const users = ref<User[] | []>([])
const userPayload = ref<AddUserPayload | null>(null)
const fetchQuery = ref<GetAllUserListQuery>({ page: 1, limit: 10 })
const isDataFetching = ref(false)
const isDeleting = ref(false)
const searchQuery = ref('')

// form
const isFormReset = ref(false)
const isFormLoading = ref(false)
const selectedUser = ref<User | null>(null)
const userFormUsage = ref('create')
const userFormTitle = ref('Add User')
const selectedUserStation = ref<string[] | []>([])

// pagination
const totalPages = ref(1)
const totalData = ref(1)
const perPage = ref(10)
const currentPage = ref(1)

const debouncedSearch = useDebounceFn(() => {
  fetchUsers()
}, 1000)

watch(
  () => searchQuery.value,
  (newValue) => {
    fetchQuery.value = { ...fetchQuery.value, page: 1, q: newValue }
    debouncedSearch()
  }
)

onMounted(() => {
  fetchUsers()
})

function resetPageProperty() {
  searchQuery.value = ''
  fetchQuery.value = { page: 1, limit: 10 }
  resetPage()
  fetchUsers()
}

function fetchUsers() {
  users.value = []
  isDataFetching.value = true
  getUsersAPI(fetchQuery.value).then(({ data, total }) => {
    users.value = data
    totalData.value = total
    totalPages.value = Math.ceil(total / perPage.value)
    isDataFetching.value = false
  })
}

function addUser() {
  isFormLoading.value = true
  postUserAPI(userPayload.value as AddUserPayload)
    .then(() => {
      isFormReset.value = true
      onUserFormModalClose()
      resetPageProperty()
      toast.success(`Berhasil menambahkan ${userPayload.value?.username}.`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .catch((e: Error) => {
      toast.error(`Gagal menambahkan ${userPayload.value?.username}. \n ${e.message}`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .finally(() => {
      isFormLoading.value = false
    })
}

function updateUser() {
  isFormLoading.value = true
  //eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { password, ...updatePayload } = userPayload.value as AddUserPayload
  putUserAPI(selectedUser.value?._id as string, updatePayload as UpdateUserPayload)
    .then(() => {
      isFormReset.value = true
      onUserFormModalClose()
      resetPageProperty()

      toast.success(`Berhasil memperbaruin ${selectedUser.value?.username}.`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .catch((e: Error) => {
      toast.error(`Gagal memperbaruin ${selectedUser.value?.username}. \n ${e.message}`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
    .finally(() => {
      isFormLoading.value = false
    })
}

function removeUser() {
  isDeleting.value = true
  deleteUserAPI(selectedUser.value?._id as string)
    .then(() => {
      onModalDeleteClose()
      resetPageProperty()
      toast.success(`Berhasil menghapus ${selectedUser.value?.username}.`, {
        autoClose: 3000,
        position: 'top-center'
      })
      selectedUser.value = null
      isDeleting.value = false
    })
    .catch((e: Error) => {
      toast.error(`Gagal menghapus ${selectedUser.value?.username}. \n ${e.message}`, {
        autoClose: 3000,
        position: 'top-center'
      })
    })
}

function resetPage() {
  fetchQuery.value = { page: 1, limit: 10 }
  currentPage.value = 1
}

function onSubmitUserForm(payload: AddUserPayload) {
  isFormReset.value = false
  userPayload.value = payload
  switch (userFormUsage.value) {
    case 'create':
      addUser()
      break
    case 'edit':
      updateUser()
      break
    default:
      toast.error(`Unregister form usage`, {
        autoClose: 3000,
        position: 'top-center'
      })
      break
  }
}

function onUserStationFormSubmit(selectedStation: string[]) {
  console.log(selectedStation)
}

function onDeleteButtonClick(user: User) {
  isDeleting.value = false
  userDeleteModalRef.value.showModal()
  selectedUser.value = user
}

function onEditButtonClick(user: User) {
  selectedUser.value = user
  userFormTitle.value = 'Edit User'
  userFormUsage.value = 'edit'
  userFormModalRef.value.showModal()
}

function onStationBadgeClick(userStations: string[]) {
  selectedUserStation.value = userStations
  userStationModalRef.value.showModal()
}

function onUserFormModalClose() {
  userFormModalRef.value.close()
}

function onModalDeleteClose() {
  userDeleteModalRef.value.close()
}

function onUserStationFormModalClose() {
  selectedUserStation.value = []
  userStationModalRef.value.close()
}

function onAddUserButtonClick() {
  userFormUsage.value = 'create'
  userFormTitle.value = 'Add User'
  selectedUser.value = null
  userFormModalRef.value.showModal()
}

function showMore(page: number) {
  currentPage.value = page
  fetchQuery.value = { ...fetchQuery.value, page }
  fetchUsers()
}
</script>

<template>
  <ConfigLayout>
    <div class="p-6 w-full h-full overflow-y-auto">
      <div class="mb-6">
        <h2 class="font-bold mb-4">User List</h2>
        <div class="flex items-center gap-4 justify-between">
          <Input v-model="searchQuery" class="max-w-80" placeholder="Search . . ." />
          <button class="btn btn-primary" @click="onAddUserButtonClick">Add User</button>
        </div>
      </div>

      <div class="w-full overflow-x-auto">
        <table class="table">
          <thead class="bg-[#2B395C] text-white">
            <tr>
              <th>Username</th>
              <th>Region</th>
              <th class="min-w-[150px]">Station</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody v-if="users.length">
            <tr v-for="user in users" :key="user._id">
              <td>{{ user.username }}</td>
              <td>{{ user.region }}</td>
              <td>
                <div
                  class="badge badge-info badge-outline rounded-md font-bold cursor-pointer"
                  @click="onStationBadgeClick(user.stations)">
                  {{ user.stations.length }} Stations
                </div>
              </td>
              <td class="flex gap-2">
                <button class="btn btn-square btn-sm btn-outline btn-error" @click="onDeleteButtonClick(user)">
                  <v-icon name="fa-regular-trash-alt" />
                </button>
                <button class="btn btn-square btn-sm btn-outline" @click="onEditButtonClick(user)">
                  <v-icon name="hi-pencil-alt" />
                </button>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr v-if="isDataFetching">
              <td colspan="4">
                <div class="flex items-center justify-center gap-2 w-full">
                  <div class="loading loading-spinner" />
                  <div>Loading...</div>
                </div>
              </td>
            </tr>
            <tr v-else>
              <td colspan="4" class="text-center">Data user not found</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mx-auto">
        <Pagination
          class="mt-4"
          :total-pages="totalPages"
          :total="totalData"
          :per-page="perPage"
          :current-page="currentPage"
          @pagechanged="showMore" />
      </div>
      <dialog ref="userFormModalRef" class="modal">
        <div class="modal-box">
          <UserForm
            :usage="userFormUsage"
            :user-data="selectedUser"
            :title="userFormTitle"
            :is-loading="isFormLoading"
            :is-reset="isFormReset"
            @on-cancel="onUserFormModalClose"
            @on-submit="onSubmitUserForm" />
          <div class="modal-action h-0 mt-0">
            <form method="dialog" class="modal-backdrop">
              <button>close</button>
            </form>
          </div>
        </div>
      </dialog>
      <dialog ref="userDeleteModalRef" class="modal">
        <div class="modal-box">
          <h3 class="text-2xl font-bold mb-4">Delete User</h3>
          <p>
            Are you sure to delete user <span class="text-rose-700 font-bold">{{ selectedUser?.username }}</span> ?
          </p>
          <div class="flex gap-4 mt-4">
            <button class="btn btn-outline btn-error btn-block shrink" @click="onModalDeleteClose">Cancel</button>
            <button class="btn btn-error btn-block shrink" @click="removeUser">
              <div v-if="isDeleting" class="loading loading-spinner" />
              <span v-else>Delete</span>
            </button>
          </div>
          <div class="modal-action h-0 mt-0">
            <form method="dialog" class="modal-backdrop">
              <button>close</button>
            </form>
          </div>
        </div>
      </dialog>
      <dialog ref="userStationModalRef" class="modal">
        <div class="modal-box">
          <UserStationForm
            :is-loading="false"
            :user-station="selectedUserStation"
            @on-cancel="onUserStationFormModalClose"
            @on-submit="onUserStationFormSubmit" />
          <div class="modal-action h-0 mt-0">
            <form method="dialog" class="modal-backdrop">
              <button>close</button>
            </form>
          </div>
        </div>
      </dialog>
    </div>
  </ConfigLayout>
</template>
