import { apiClient } from './client'
import type { ProviderCatalog, EstimateCostParams, CostEstimateResponse } from './catalog.types'

export const catalogApi = {
  async getCatalog(): Promise<ProviderCatalog> {
    const response = await apiClient.get('/catalog/models')
    return response.data
  },

  async estimateCost(params: EstimateCostParams): Promise<CostEstimateResponse> {
    const response = await apiClient.post('/catalog/estimate', params)
    return response.data
  }
}
