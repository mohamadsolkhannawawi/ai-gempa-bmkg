import { StationWaveForm } from '@src/types/waveform'

export const getStartIndex = (waveform: StationWaveForm, startTime: number) => {
  const waveformStartTime = new Date(waveform.starttime).getTime()
  if (waveformStartTime >= startTime) return 0
  const diffSeconds = (startTime - waveformStartTime) / 1000
  return parseInt(Math.ceil(diffSeconds / waveform.delta).toFixed(0), 10)
}
