import { API_BFF_URL } from '@src/constants/env'
import { AddStationPayload, Station, StationWaveformStatus } from '@src/types/station'
import api from '@src/utils/api'

import { GetStationListQuery, PutUpdateStationStatusPayload } from './types'

export const putUpdateStationStatusAPI = async (payload: PutUpdateStationStatusPayload) => {
  const { data } = await api.put('/station/updatestatus', payload)
  return data
}

export const getStationListAPI = async (useRealAPI = false, params?: GetStationListQuery) => {
  const { data } = await api.get<{ data: { stations: Station[]; total?: number } }>('/station/getall')
  return { data: data.data.stations, total: data.data.total }
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
  const { data } = await api.post('/station', payload)

  return data
}

export const putStationAPI = async (stationId: string, payload: AddStationPayload) => {
  const { data } = await api.put(`/station/${stationId}`, payload)

  return data
}

export const deleteStationAPI = async (stationId: string) => {
  const { data } = await api.delete(`/station/${stationId}`)

  return data
}
