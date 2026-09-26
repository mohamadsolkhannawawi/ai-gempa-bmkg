import { Pick } from './pick'
import { Station } from './station'

export interface Arrival {
  _id: string
  pick_source_id: Pick
  pick_details: Pick
  station_id: Station
  station_details: Station
  timestamp: string
  phase_type: string
  created_at: string
  checked?: boolean
}
