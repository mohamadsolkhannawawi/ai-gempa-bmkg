import { Arrival } from '@src/types/arrival'

export interface GetAllEventListQuery {
  page: number
  totalPerPage: number
  startDate?: string
  endDate?: string
}

export interface PutEventCommitAPIArrival extends Omit<Arrival, 'pick_source_id' | 'station_id'> {
  pick_source_id: string
  station_id: string
}
