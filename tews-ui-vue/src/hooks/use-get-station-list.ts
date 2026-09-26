import { getStationListAPI } from '@src/api-service/station'
import { useQuery } from '@tanstack/vue-query'

const useGetStationList = (useRealAPI = false) =>
  useQuery({
    queryKey: ['station-list'],
    queryFn: () => getStationListAPI(useRealAPI)
  })

export default useGetStationList
