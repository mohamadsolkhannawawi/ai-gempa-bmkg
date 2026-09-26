export interface APIResponse<T> {
  status: boolean
  message: string
  data: T | null
}
