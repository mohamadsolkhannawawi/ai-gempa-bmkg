export type PhaseType = 'P' | 'S'

export type OrderPhaseType = PhaseType | 'OT'

export interface StationWaveForm {
  date: string
  starttime: string
  endtime: string
  sampling_rate: number
  delta: number
  location: string
  npts: number
  station: string
  network: string
  channel: string
  expiration_timestamp: number
  waveform: number[]
}

export interface WaveFormChartData {
  time: number
  amplitude: number
}

export interface RealtimePick {
  _id: string
  station?: string
  timestamp: string
  created_at?: string
}

export interface RealtimeArrival {
  _id: string
  pick_source_id: string
  station?: string
  timestamp: string
  phase_type: PhaseType
  created_at?: string
}
export interface WebsocketPickingResponse {
  network: string
  station: string
  picks: {
    _id: string
    timestamp: string
  }[]
}

export interface WebsocketArrivalPick {
  _id: string
  timestamp: string
  type: PhaseType
}

export interface WebsocketArrivalResponse {
  pick_source_id: string
  station_id: string
  network: string
  station: string
  longitude: number
  latitude: number
  picks: WebsocketArrivalPick[]
}
