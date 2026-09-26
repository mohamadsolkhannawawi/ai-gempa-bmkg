import { EarthQuakeEvent, EventCommitResponse } from '@src/types/event'
import api from '@src/utils/api'

import { GetAllEventListQuery, PutEventCommitAPIArrival } from './types'

export const getEventListByDateAPI = async (startTime: number, endTime: number) => {
  const { data } = await api.get<{ data: EarthQuakeEvent[] }>('/event/getbybetweendate', {
    params: {
      start_date: startTime,
      end_date: endTime
    }
  })
  return data.data
}

export const getAllEventListAPI = async (params: GetAllEventListQuery) => {
  const { data } = await api.get<{ data: EarthQuakeEvent[]; total: number }>('/event/getall', {
    params: {
      page: params.page,
      total_per_page: params.totalPerPage,
      start_date: params.startDate,
      end_date: params.endDate
    }
  })
  return {
    ...data,
    total: data.total ?? 1
  }
}

export const getEventDetailAPI = async (eventId: string) => {
  const { data } = await api.get<{ data: EarthQuakeEvent }>('/event/getdetail', {
    params: {
      event_id: eventId
    }
  })

  const eventDetail = data.data
  const sortedArrivals = [...eventDetail.arrivals]

  sortedArrivals.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())

  return {
    ...eventDetail,
    arrivals: sortedArrivals
  }
}

export const putEventCommitAPI = async (eventId: string, arrivals: PutEventCommitAPIArrival[]) => {
  const { data } = await api.put<{ status: boolean; data: EventCommitResponse }>('/event/commit', {
    event_id: eventId,
    arrival_list: arrivals
  })

  return data
}
