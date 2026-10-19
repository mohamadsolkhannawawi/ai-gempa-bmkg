import { defineStore } from 'pinia'
import { ref } from 'vue'
import { catalogApi } from '@/services/api/catalog'
import type { ProviderCatalog, ModelTier, EstimateCostParams } from '@/services/api/catalog.types'

export const useCatalogStore = defineStore('catalog', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const catalog = ref<ProviderCatalog | null>(null)
  const providers = ref<ModelTier[]>([])
  const estimate = ref<{ total_idr: number; breakdown: Array<{ provider: string; cost_idr: number }> } | null>(null)

  async function fetchCatalog() {
    loading.value = true
    error.value = null
    try {
      const data = await catalogApi.getCatalog()
      catalog.value = data
      providers.value = data.providers
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch catalog'
    } finally {
      loading.value = false
    }
  }

  async function estimateCost(params: EstimateCostParams) {
    loading.value = true
    error.value = null
    try {
      const result = await catalogApi.estimateCost(params)
      estimate.value = result
      return result
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to estimate cost'
      throw err
    } finally {
      loading.value = false
    }
  }

  function getProviderById(id: string) {
    return providers.value.find(p => p.id === id)
  }

  function getProviderCostEstimate(providerId: string, tier: 'cpu' | 'gpu', inferences: number): number | null {
    const provider = getProviderById(providerId)
    if (!provider) return null

    const tierConfig = provider.tiers.find(t => t.name === tier)
    if (!tierConfig) return null

    return tierConfig.cost_per_inference * inferences
  }

  function clearEstimate() {
    estimate.value = null
  }

  return {
    loading,
    error,
    catalog,
    providers,
    estimate,
    fetchCatalog,
    estimateCost,
    getProviderById,
    getProviderCostEstimate,
    clearEstimate
  }
})
