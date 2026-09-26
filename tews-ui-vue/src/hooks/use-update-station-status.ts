import api from '@src/utils/api'
import { useMutation } from '@tanstack/vue-query'

interface UpdateStatusPayload {
  stationId: string
  enabled: boolean
}

const useUpdateStationStatus = () =>
  useMutation({
    mutationFn: (payload: UpdateStatusPayload) =>
      api.put('/station/updatestatus', {
        station_id: payload.stationId,
        status: payload.enabled ? 'enable' : 'disable'
      })
  })

export default useUpdateStationStatus
