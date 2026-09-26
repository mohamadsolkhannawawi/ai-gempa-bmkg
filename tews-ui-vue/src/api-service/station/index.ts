import { API_BFF_URL } from '@src/constants/env'
import { AddStationPayload, Station, StationWaveformStatus } from '@src/types/station'
import api from '@src/utils/api'

import { GetStationListQuery, PutUpdateStationStatusPayload } from './types'

export const putUpdateStationStatusAPI = async (payload: PutUpdateStationStatusPayload) => {
  const { data } = await api.put('/station/updatestatus', payload)
  return data
}

export const getStationListAPI = async (useRealAPI = false, params?: GetStationListQuery) => {
  if (useRealAPI) {
    const { data } = await api.get<{ data: Station[]; total?: number }>('/station/getall')
    return data
  }

  const { data } = await api.get<{ data: Station[]; total?: number }>('/station', {
    baseURL: API_BFF_URL,
    params: {
      page: params?.page ?? 1,
      limit: params?.limit ?? 10,
      ...(params?.q && { q: params?.q })
    }
  })

  return data
}

export const getStationWaveformStatusAPI = async (stationId: string) => {
  const { data } = await api.get<{ data: StationWaveformStatus }>('/station/getwaveformstatus', {
    params: {
      station_id: stationId
    }
  })

  return data
}

export const postStationAPI = async (payload: AddStationPayload) => {
  const { data } = await api.post('/station', payload, {
    baseURL: API_BFF_URL
  })

  return data
}

export const putStationAPI = async (stationId: string, payload: AddStationPayload) => {
  const { data } = await api.put(`/station/${stationId}`, payload, {
    baseURL: API_BFF_URL
  })

  return data
}

export const deleteStationAPI = async (stationId: string) => {
  const { data } = await api.delete(`/station/${stationId}`, {
    baseURL: API_BFF_URL
  })

  return data
}
