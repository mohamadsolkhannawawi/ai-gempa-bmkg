import { getStationWaveformStatusAPI } from '@src/api-service/station'
import { useQuery } from '@tanstack/vue-query'

const useGetStationWaveformStatus = (stationId: string) =>
  useQuery({
    queryKey: ['station-list', stationId],
    queryFn: () => getStationWaveformStatusAPI(stationId),
    refetchInterval: 5000,
    refetchOnWindowFocus: true
  })

export default useGetStationWaveformStatus
