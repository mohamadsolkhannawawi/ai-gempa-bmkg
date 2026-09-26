import axios, { AxiosError } from 'axios'
import Cookies from 'js-cookie'

import { API_BASE_URL } from '../constants/env'

const COOKIE_ACCESS_TOKEN_KEY = 'access_token'

const api = axios.create({
  baseURL: API_BASE_URL
})

api.interceptors.request.use((config) => {
  const token = Cookies.get(COOKIE_ACCESS_TOKEN_KEY)

  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }

  return config
})

api.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError) => {
    const hasCookie = Cookies.get(COOKIE_ACCESS_TOKEN_KEY)
    if (error.response?.status === 401) {
      if (hasCookie) {
        Cookies.remove(COOKIE_ACCESS_TOKEN_KEY)
        location.reload()
      }
    }

    return Promise.reject(error)
  }
)

export default api
