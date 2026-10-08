import { Station } from '../types/station'

export const getChannelByOrder = (station: Station, channels: string[]) => {
  for (const channel of channels) {
    if (station.channel.includes(channel)) {
      return channel
    }
  }
  return null
}

export const getStationByChannel = (stations: Station[], channels: string[]) => {
  if (!channels.length) return stations
  return stations.filter((station) => {
    return channels.some((channel) => station.channel.includes(channel))
  })
}

export const getChannelFullName = (station: Station, channelName: string) => {
  // Normalize null/undefined location to empty string (matches backend behavior)
  const loc = station.location ?? ''
  return `${station.network}.${station.code}.${loc}.${channelName}`
}
