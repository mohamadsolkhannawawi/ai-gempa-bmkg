import { Arrival } from './arrival'
import { Cluster } from './cluster'
import { Magnitude } from './magnitude'

export interface EarthQuakeEvent {
  _id: string
  name: string
  // cluster_id: Cluster
  cluster_detail: Cluster[]
  arrival_ids: string[]
  arrivals: Arrival[]
  longitude: number
  latitude: number
  depth: number
  region: string
  sub_region: string
  terrain: string
  country: string
  // magnitude_ids: Magnitude[]
  magnitudes: Magnitude[]
  created_at: string
}

export interface EventCommitResponse {
  _id: string
}
