import { putEventCommitAPI } from '@src/api-service/event'
import { PutEventCommitAPIArrival } from '@src/api-service/event/types'
import { useMutation } from '@tanstack/vue-query'

interface UsePutEventCommitProps {
  eventId: string
  arrivals: PutEventCommitAPIArrival[]
}

const usePutEventCommit = () =>
  useMutation({
    mutationFn: (data: UsePutEventCommitProps) => putEventCommitAPI(data.eventId, data.arrivals)
  })

export default usePutEventCommit
