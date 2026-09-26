import { EarthQuakeEvent } from '@src/types/event'
import { Magnitude } from '@src/types/magnitude'
// import { format } from 'date-fns'

export const formatDate = (date: string | Date) => {
  // const strFormat = 'd/M/yyyy pp'
  if (typeof date === 'string') {
    // return format(newISODate(date), strFormat)
    return newISODate(date).toISOString()
  }
  // return format(date, strFormat)
  return date.toISOString()
}

export const newISODate = (date: string) => {
  return new Date(date.includes('T') && !date.includes('Z') ? `${date}Z` : date)
}

export const getDefaultMagnitude = (magnitudes: Magnitude[]) =>
  magnitudes.find((magnitude) => magnitude.type.toLowerCase() === 'mw')

export const getOriginTimeFromEvent = (event: EarthQuakeEvent) => event.cluster_detail?.[0]?.origin_time

export const formatMagnitude = (magnitude: number) => magnitude?.toFixed(1)
export const formatDepth = (depth: number) => depth?.toFixed(1)
export const formatLatLon = (coordinate: number) => coordinate?.toFixed(3)

export const timeAgo = (date: Date) => {
  const now = new Date()
  const secondsAgo = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (secondsAgo < 60) {
    return secondsAgo === 1 ? 'baru saja' : `${secondsAgo} detik lalu`
  }

  const minutesAgo = Math.floor(secondsAgo / 60)
  if (minutesAgo < 60) {
    return `${minutesAgo} menit lalu`
  }

  const hoursAgo = Math.floor(minutesAgo / 60)
  return `${hoursAgo} jam lalu`
}
