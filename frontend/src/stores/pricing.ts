import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pricingApi } from '@/services/api/pricing'
import type {
  Invoice,
  UsageStatement,
  EstimateRequest,
  EstimateResponse
} from '@/services/api/pricing.types'

export const usePricingStore = defineStore('pricing', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const invoices = ref<Invoice[]>([])
  const currentInvoice = ref<Invoice | null>(null)
  const usageStatement = ref<UsageStatement | null>(null)
  const estimate = ref<EstimateResponse | null>(null)

  async function fetchInvoices(workspaceId?: string, status?: string) {
    loading.value = true
    error.value = null
    try {
      const data = await pricingApi.getInvoices({ workspace_id: workspaceId, status })
      invoices.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch invoices'
    } finally {
      loading.value = false
    }
  }

  async function fetchInvoiceById(id: string) {
    loading.value = true
    error.value = null
    try {
      const data = await pricingApi.getInvoice(id)
      currentInvoice.value = data
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch invoice'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUsageStatement(workspaceId: string, startDate: string, endDate: string) {
    loading.value = true
    error.value = null
    try {
      const data = await pricingApi.getUsageStatement(workspaceId, startDate, endDate)
      usageStatement.value = data
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch usage statement'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function estimateCost(request: EstimateRequest) {
    loading.value = true
    error.value = null
    try {
      const data = await pricingApi.estimateCost(request)
      estimate.value = data
      return data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to estimate cost'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function downloadInvoice(invoiceNumber: string) {
    loading.value = true
    error.value = null
    try {
      const blob = await pricingApi.downloadInvoice(invoiceNumber)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${invoiceNumber}.pdf`
      link.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to download invoice'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearEstimate() {
    estimate.value = null
  }

  return {
    loading,
    error,
    invoices,
    currentInvoice,
    usageStatement,
    estimate,
    fetchInvoices,
    fetchInvoiceById,
    fetchUsageStatement,
    estimateCost,
    downloadInvoice,
    clearEstimate
  }
})
