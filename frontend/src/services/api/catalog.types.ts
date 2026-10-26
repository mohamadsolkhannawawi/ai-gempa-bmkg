export interface ModelTier {
  id: string
  name: string
  provider: string
  module: 'p_pick' | 'association' | 'locmag'
  tiers: Array<{
    name: 'cpu' | 'gpu'
    available: boolean
    cost_per_inference: number
  }>
}

export interface ProviderCatalog {
  providers: ModelTier[]
  total_count: number
}

export interface EstimateCostParams {
  profile_config: {
    p_pick?: { provider: string; tier: string; inferences?: number }
    association?: { provider: string; tier: string; inferences?: number }
    locmag?: { provider: string; tier: string; inferences?: number }
  }
  expected_inferences?: number
}

export interface CostEstimateResponse {
  total_idr: number
  breakdown: Array<{
    provider: string
    cost_idr: number
  }>
}
