import { getEventDetailAPI } from '@src/api-service/event'
import { useQuery } from '@tanstack/vue-query'

const useGetEventDetail = (eventId: string) =>
  useQuery({
    enabled: !!eventId,
    queryKey: ['event-detail', eventId],
    queryFn: () => getEventDetailAPI(eventId)
  })

export default useGetEventDetail
