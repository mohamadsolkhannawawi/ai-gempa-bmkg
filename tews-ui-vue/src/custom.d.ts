import 'leaflet'
import { Station } from 'types/station'

declare module 'leaflet' {
  interface MarkerOptions {
    station?: Station
  }
}
