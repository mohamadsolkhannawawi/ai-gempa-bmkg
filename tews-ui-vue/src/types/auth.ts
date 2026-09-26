export interface SuccessLoginResponse {
  status: true
  data: {
    id: string
    username: string
    region: string
    access_token: string
  }
}

export interface FailedLoginResponse {
  status: false
  data: null
}

export type LoginResponse = SuccessLoginResponse | FailedLoginResponse
