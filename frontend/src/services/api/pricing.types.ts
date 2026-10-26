export interface Invoice {
  id: string
  invoice_number: string
  workspace_id: string
  period_start: string
  period_end: string
  due_date: string
  subtotal_idr: number
  tax_idr: number
  total_idr: number
  status: 'DRAFT' | 'ISSUED' | 'PAID' | 'OVERDUE' | 'VOID'
  line_items: Array<{
    description: string
    quantity: number
    unit_price: number
    amount: number
  }>
  created_at: string
  updated_at: string
}

export interface UsageStatement {
  workspace_id: string
  period_start: string
  period_end: string
  total_inferences: number
  total_cost_idr: number
  breakdown_by_provider: Record<string, number>
  breakdown_by_module: Record<string, number>
}

export interface EstimateRequest {
  profile_config: {
    p_pick?: { provider: string; tier: string }
    association?: { provider: string; tier: string }
    locmag?: { provider: string; tier: string }
  }
  expected_monthly_inferences: number
}

export interface EstimateResponse {
  subtotal_idr: number
  tax_idr: number
  total_idr: number
  breakdown: Array<{
    module: string
    provider: string
    inferences: number
    cost_idr: number
  }>
}
