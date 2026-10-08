export interface Station {
  _id: string
  name: string
  code: string
  network: string
  location: string
  channel: string[]
  longitude: number
  latitude: number
  elevation: number
  server_seedlink: string
  server_fdsn: string
  status?: 'enabled' | 'disabled'
}

export interface StationWaveformStatus extends Station {
  delay_second: number
  spike_amplitude: number
  displacement: number
  velocity: number
  acceleration: number
  rms?: number
  spikes_count?: number
  spikes_interval?: number
  timing_quality?: number
}

export interface UpdateStationPayload extends Omit<Station, '_id'> {
  station_id: string
}

export type AddStationPayload = Omit<Station, '_id' | 'location' | 'status'>
