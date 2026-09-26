import { RealtimeArrival, RealtimePick } from './types/waveform'

declare global {
  interface Window {
    socketData: Record<
      string,
      {
        picks: Record<string, RealtimePick>
        arrivals: Record<string, RealtimeArrival[]>
      }
    >
  }
}
