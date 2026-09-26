export interface User {
  _id: string
  username: string
  role: string
  region: string
  stations: string[]
  disable_stations: string[]
}

export interface AddUserPayload {
  username: string
  password: string
  region: string
}

export interface AddStationToUserPayload {
  user_id: string
  station_id: string[]
}

export type UpdateUserPayload = Omit<AddUserPayload, 'password'>
