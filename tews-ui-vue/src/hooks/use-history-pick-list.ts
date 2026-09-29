import { API_BFF_URL } from '@src/constants/env'
import { RealtimeArrival, RealtimePick } from '@src/types/waveform'
import api from '@src/utils/api'
import { useQuery } from '@tanstack/vue-query'
import { subMinutes } from 'date-fns'
import { watch } from 'vue'

const useHistoryPickList = (stationId: string, channelName: string) => {
  const endDate = new Date()
  const startDate = subMinutes(endDate, 30)

  const params = {
    startDate: startDate.toISOString(),
    endDate: endDate.toISOString()
  }

  const { data: arrivalListData } = useQuery({
    queryKey: ['history-arrival-list', stationId],
    queryFn: () =>
      api.get<RealtimeArrival[]>(`/arrival/getbystation?station_id=${stationId}`, {
        baseURL: API_BFF_URL,
        params
      })
  })

  const { data: pickListData, refetch: refetchPickList } = useQuery({
    enabled: false,
    queryKey: ['history-pick-list', stationId],
    queryFn: () =>
      api.get<RealtimePick[]>(`/station/${stationId}/pick`, {
        baseURL: API_BFF_URL,
        params
      })
  })

  watch(arrivalListData, (newData) => {
    const arrivals = (newData?.data ?? []).filter(
      (arrival) => new Date(arrival.timestamp).getTime() > subMinutes(Date.now(), 30).getTime()
    )
    const windowArrivals: Record<string, RealtimeArrival[]> = {}

    for (const arrival of arrivals) {
      if (!windowArrivals[arrival.pick_source_id]) {
        windowArrivals[arrival.pick_source_id] = [arrival]
      } else {
        windowArrivals[arrival.pick_source_id].push(arrival)
      }
    }

    if (!window.socketData[channelName]) {
      window.socketData[channelName] = {
        picks: {},
        arrivals: windowArrivals
      }
    } else {
      window.socketData[channelName].arrivals = windowArrivals
    }

    refetchPickList()
  })

  watch(pickListData, (newData) => {
    const picks = newData?.data ?? []

    for (const pick of picks) {
      if (!window.socketData[channelName].arrivals[pick._id]) {
        window.socketData[channelName].picks[pick._id] = pick
      }
    }
  })
}

export default useHistoryPickList
