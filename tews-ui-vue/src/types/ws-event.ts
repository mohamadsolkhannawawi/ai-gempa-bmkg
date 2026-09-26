export interface WSEvent {
  cluster: Cluster
  arrivals: Arrivals
  longitude: number
  latitude: number
  depth: number
  magnitudes: Magnitude[]
  modified_by: string
  id: string
  region: string
  sub_region: string
}

export interface Cluster {
  id: string
  picks: string[]
  network: string
  station: string
  timestamp: string
  origin_time: string
}

export interface Arrivals {
  P: P
  S: S
}

export interface P {
  id: string
  timestamp: string
  modified_by: string
}

export interface S {
  id: string
  timestamp: string
  modified_by: string
}

export interface Magnitude {
  type: string
  value: number
  modified_by: string
  id: string
}
