const USE_MOCK = window.localStorage.getItem('use-mock') === 'true'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL
export const API_BASE_URL_MOCK: string = USE_MOCK ? import.meta.env.VITE_API_BASE_URL_MOCK : API_BASE_URL
export const SOCKET_BASE_URL = import.meta.env.VITE_SOCKET_BASE_URL
export const SOCKET_ALTERNATIVE_BASE_URL = import.meta.env.VITE_SOCKET_ALTERNATIVE_BASE_URL
export const SOCKET_IO_BASE_URL = USE_MOCK
  ? import.meta.env.VITE_SOCKET_IO_BASE_URL_MOCK
  : import.meta.env.VITE_SOCKET_IO_BASE_URL
export const MAP_HOST: string = import.meta.env.VITE_MAP_HOST
export const API_BFF_URL: string = import.meta.env.VITE_API_BFF_URL
export const API_STREAM_URL: string = import.meta.env.VITE_API_STREAM_URL
