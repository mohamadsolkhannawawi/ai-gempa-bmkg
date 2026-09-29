import { API_BFF_URL } from '@src/constants/env'
import { AddUserPayload, UpdateUserPayload, User } from '@src/types/user'
import api from '@src/utils/api'

import { GetAllUserListQuery } from './types'

export const getUsersAPI = async (params?: GetAllUserListQuery) => {
  const { data } = await api.get<{ data: User[]; total: number }>('/user/getall', {
    params: {
      page: params?.page ?? 1,
      limit: params?.limit ?? 10,
      ...(params?.q && { q: params.q })
    }
  })

  return data
}

export const postUserAPI = async (payload: AddUserPayload) => {
  const { data } = await api.post('/user', payload)
  return data
}

export const deleteUserAPI = async (userId: string) => {
  const { data } = await api.delete(`/user/${userId}`)

  return data
}

export const putUserAPI = async (userId: string, payload: UpdateUserPayload) => {
  const { data } = await api.put(`/user/${userId}`, payload)
  return data
}
