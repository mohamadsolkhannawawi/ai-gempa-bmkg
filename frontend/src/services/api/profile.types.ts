export interface Profile {
  id: string
  workspace_id: string
  name: string
  description?: string
  config: {
    p_pick?: { provider: string; tier: string; config?: any }
    association?: { provider: string; tier: string; config?: any }
    locmag?: { provider: string; tier: string; config?: any }
  }
  compiled_sha256?: string
  active: boolean
  created_at: string
  updated_at: string
}

export interface ProfileCreateRequest {
  workspace_id: string
  name: string
  description?: string
  config: Profile['config']
}

export interface ProfileUpdateRequest {
  name?: string
  description?: string
  config?: Profile['config']
  active?: boolean
}

export interface ProfileCompileRequest {
  force?: boolean
}

export interface CostEstimate {
  profile_id: string
  estimated_cost_per_inference: number
  monthly_estimate: number
  breakdown: Array<{
    module: string
    provider: string
    cost_per_inference: number
  }>
}
