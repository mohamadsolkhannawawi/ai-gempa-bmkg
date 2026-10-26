import { apiClient } from './client'
import type {
  Profile,
  ProfileCreateRequest,
  ProfileUpdateRequest,
  ProfileCompileRequest,
  CostEstimate
} from './profile.types'

export const profileApi = {
  async getProfiles(): Promise<Profile[]> {
    const response = await apiClient.get('/profiles')
    return response.data
  },

  async getProfile(id: string): Promise<Profile> {
    const response = await apiClient.get(`/profiles/${id}`)
    return response.data
  },

  async createProfile(request: ProfileCreateRequest): Promise<Profile> {
    const response = await apiClient.post('/profiles', request)
    return response.data
  },

  async updateProfile(id: string, request: ProfileUpdateRequest): Promise<Profile> {
    const response = await apiClient.put(`/profiles/${id}`, request)
    return response.data
  },

  async compileProfile(id: string, request: ProfileCompileRequest): Promise<{ sha256: string }> {
    const response = await apiClient.post(`/profiles/${id}/compile`, request)
    return response.data
  },

  async deleteProfile(id: string): Promise<void> {
    await apiClient.delete(`/profiles/${id}`)
  },

  async estimateCost(id: string): Promise<CostEstimate> {
    const response = await apiClient.get(`/profiles/${id}/estimate`)
    return response.data
  }
}
