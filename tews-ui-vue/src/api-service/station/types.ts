export interface PutUpdateStationStatusPayload {
  station_id: string
  status: 'enabled' | 'disabled'
}

export interface GetStationListQuery {
  page: number
  limit: number
  q?: string
}
