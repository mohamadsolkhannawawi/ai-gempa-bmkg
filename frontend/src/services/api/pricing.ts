import { apiClient } from './client'
import type { Invoice, UsageStatement, EstimateRequest, EstimateResponse } from './pricing.types'

export const pricingApi = {
  async getInvoices(params?: { workspace_id?: string; status?: string }): Promise<Invoice[]> {
    const response = await apiClient.get('/billing/invoices', { params })
    return response.data
  },

  async getInvoice(id: string): Promise<Invoice> {
    const response = await apiClient.get(`/billing/invoices/${id}`)
    return response.data
  },

  async getUsageStatement(workspaceId: string, startDate: string, endDate: string): Promise<UsageStatement> {
    const response = await apiClient.get('/billing/usage', {
      params: {
        workspace_id: workspaceId,
        start_date: startDate,
        end_date: endDate
      }
    })
    return response.data
  },

  async estimateCost(request: EstimateRequest): Promise<EstimateResponse> {
    const response = await apiClient.post('/pricing/estimate', request)
    return response.data
  },

  async downloadInvoice(invoiceNumber: string): Promise<Blob> {
    const response = await apiClient.get(`/billing/invoices/${invoiceNumber}/pdf`, {
      responseType: 'blob'
    })
    return response.data
  }
}
