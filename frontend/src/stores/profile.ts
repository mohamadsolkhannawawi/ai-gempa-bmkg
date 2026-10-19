import { defineStore } from 'pinia'
import { ref } from 'vue'
import { profileApi } from '@/services/api/profile'
import type {
  Profile,
  ProfileCreateRequest,
  ProfileUpdateRequest,
  ProfileCompileRequest,
  CostEstimate
} from '@/services/api/profile.types'

export const useProfileStore = defineStore('profile', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const profiles = ref<Profile[]>([])
  const currentProfile = ref<Profile | null>(null)
  const costEstimate = ref<CostEstimate | null>(null)

  async function fetchProfiles() {
    loading.value = true
    error.value = null
    try {
      const data = await profileApi.getProfiles()
      profiles.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch profiles'
    } finally {
      loading.value = false
    }
  }

  async function fetchProfileById(id: string) {
    loading.value = true
    error.value = null
    try {
      const data = await profileApi.getProfile(id)
      currentProfile.value = data
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch profile'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createProfile(request: ProfileCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const data = await profileApi.createProfile(request)
      profiles.value.push(data)
      currentProfile.value = data
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create profile'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(id: string, request: ProfileUpdateRequest) {
    loading.value = true
    error.value = null
    try {
      const data = await profileApi.updateProfile(id, request)
      const index = profiles.value.findIndex(p => p.id === id)
      if (index !== -1) {
        profiles.value[index] = data
      }
      if (currentProfile.value?.id === id) {
        currentProfile.value = data
      }
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update profile'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function compileProfile(id: string, request: ProfileCompileRequest) {
    loading.value = true
    error.value = null
    try {
      const data = await profileApi.compileProfile(id, request)
      const profile = await profileApi.getProfile(id)
      currentProfile.value = profile
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to compile profile'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteProfile(id: string) {
    loading.value = true
    error.value = null
    try {
      await profileApi.deleteProfile(id)
      profiles.value = profiles.value.filter(p => p.id !== id)
      if (currentProfile.value?.id === id) {
        currentProfile.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete profile'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function estimateCost(id: string) {
    loading.value = true
    error.value = null
    try {
      const data = await profileApi.estimateCost(id)
      costEstimate.value = data
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to estimate cost'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearCurrentProfile() {
    currentProfile.value = null
  }

  return {
    loading,
    error,
    profiles,
    currentProfile,
    costEstimate,
    fetchProfiles,
    fetchProfileById,
    createProfile,
    updateProfile,
    compileProfile,
    deleteProfile,
    estimateCost,
    clearCurrentProfile
  }
})
