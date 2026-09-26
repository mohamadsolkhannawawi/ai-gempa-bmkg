import { getAllEventListAPI } from '@src/api-service/event'
import { GetAllEventListQuery } from '@src/api-service/event/types'
import { useQuery } from '@tanstack/vue-query'

const useGetAllEventList = (params: GetAllEventListQuery) =>
  useQuery({
    queryKey: ['all-event-list', params ? params : {}],
    queryFn: () => getAllEventListAPI(params)
  })

export default useGetAllEventList
