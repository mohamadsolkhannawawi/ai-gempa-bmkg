import { getRecordStreamAPI } from '@src/api-service/record-stream'
import { GetRecordStreamAPIProps } from '@src/api-service/record-stream/types'
import { useQuery } from '@tanstack/vue-query'

const useGetRecordStream = (props: GetRecordStreamAPIProps) =>
  useQuery({
    queryKey: ['record-stream', props],
    queryFn: () => getRecordStreamAPI(props)
  })

export default useGetRecordStream
