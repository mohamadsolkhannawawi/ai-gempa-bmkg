import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCatalogStore } from '@/stores/catalog'
import { useProfileStore } from '@/stores/profile'
import { usePricingStore } from '@/stores/pricing'

// Mock API
vi.mock('@/services/api/catalog', () => ({
  catalogApi: {
    getCatalog: vi.fn(() => Promise.resolve({
      providers: [
        {
          id: 'stalta',
          name: 'STALTA',
          module: 'p_pick',
          tiers: [{ name: 'cpu', available: true, cost_per_inference: 5 }]
        }
      ],
      total_count: 1
    })),
    estimateCost: vi.fn(() => Promise.resolve({
      total_idr: 100000,
      breakdown: [{ provider: 'STALTA', cost_idr: 100000 }]
    }))
  }
}))

vi.mock('@/services/api/profile', () => ({
  profileApi: {
    getProfiles: vi.fn(() => Promise.resolve([])),
    getProfile: vi.fn((id) => Promise.resolve({
      id,
      workspace_id: 'ws_test',
      name: 'Test Profile',
      config: {},
      active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })),
    createProfile: vi.fn((req) => Promise.resolve({
      id: 'prof_001',
      workspace_id: req.workspace_id,
      name: req.name,
      config: req.config,
      active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })),
    updateProfile: vi.fn((id, req) => Promise.resolve({
      id,
      workspace_id: 'ws_test',
      name: req.name || 'Updated Profile',
      config: req.config || {},
      active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })),
    deleteProfile: vi.fn(() => Promise.resolve()),
    estimateCost: vi.fn((id) => Promise.resolve({
      profile_id: id,
      estimated_cost_per_inference: 50,
      monthly_estimate: 5000000,
      breakdown: []
    }))
  }
}))

vi.mock('@/services/api/pricing', () => ({
  pricingApi: {
    getInvoices: vi.fn(() => Promise.resolve([])),
    getInvoice: vi.fn((id) => Promise.resolve({
      id,
      invoice_number: 'INV-001',
      workspace_id: 'ws_test',
      period_start: '2026-10-01',
      period_end: '2026-10-31',
      due_date: '2026-11-15',
      subtotal_idr: 1000000,
      tax_idr: 110000,
      total_idr: 1110000,
      status: 'ISSUED',
      line_items: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })),
    getUsageStatement: vi.fn(() => Promise.resolve({
      workspace_id: 'ws_test',
      period_start: '2026-10-01',
      period_end: '2026-10-31',
      total_inferences: 100000,
      total_cost_idr: 1000000,
      breakdown_by_provider: {},
      breakdown_by_module: {}
    })),
    estimateCost: vi.fn(() => Promise.resolve({
      subtotal_idr: 1000000,
      tax_idr: 110000,
      total_idr: 1110000,
      breakdown: []
    })),
    downloadInvoice: vi.fn(() => Promise.resolve(new Blob()))
  }
}))

describe('Catalog Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty state', () => {
    const store = useCatalogStore()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.catalog).toBeNull()
    expect(store.providers).toEqual([])
  })

  it('fetches catalog successfully', async () => {
    const store = useCatalogStore()
    await store.fetchCatalog()

    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.providers.length).toBeGreaterThan(0)
  })

  it('gets provider by ID', async () => {
    const store = useCatalogStore()
    await store.fetchCatalog()

    const provider = store.getProviderById('stalta')
    expect(provider).toBeDefined()
    expect(provider?.name).toBe('STALTA')
  })

  it('estimates cost', async () => {
    const store = useCatalogStore()
    const result = await store.estimateCost({
      profile_config: {},
      expected_inferences: 1000
    })

    expect(result.total_idr).toBeGreaterThan(0)
  })
})

describe('Profile Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty state', () => {
    const store = useProfileStore()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.profiles).toEqual([])
    expect(store.currentProfile).toBeNull()
  })

  it('creates profile', async () => {
    const store = useProfileStore()
    const profile = await store.createProfile({
      workspace_id: 'ws_test',
      name: 'Test Profile',
      config: {}
    })

    expect(profile.id).toBe('prof_001')
    expect(profile.name).toBe('Test Profile')
    expect(store.profiles.length).toBe(1)
  })

  it('updates profile', async () => {
    const store = useProfileStore()
    await store.createProfile({
      workspace_id: 'ws_test',
      name: 'Test',
      config: {}
    })

    const updated = await store.updateProfile('prof_001', {
      name: 'Updated'
    })

    expect(updated.name).toBe('Updated')
  })

  it('deletes profile', async () => {
    const store = useProfileStore()
    await store.createProfile({
      workspace_id: 'ws_test',
      name: 'Test',
      config: {}
    })

    expect(store.profiles.length).toBe(1)

    await store.deleteProfile('prof_001')
    expect(store.profiles.length).toBe(0)
  })

  it('estimates cost for profile', async () => {
    const store = useProfileStore()
    const estimate = await store.estimateCost('prof_001')

    expect(estimate.estimated_cost_per_inference).toBeGreaterThan(0)
  })
})

describe('Pricing Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty state', () => {
    const store = usePricingStore()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.invoices).toEqual([])
  })

  it('fetches invoices', async () => {
    const store = usePricingStore()
    await store.fetchInvoices()

    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(Array.isArray(store.invoices)).toBe(true)
  })

  it('fetches invoice by ID', async () => {
    const store = usePricingStore()
    const invoice = await store.fetchInvoiceById('inv_001')

    expect(invoice.id).toBe('inv_001')
    expect(invoice.invoice_number).toBe('INV-001')
  })

  it('fetches usage statement', async () => {
    const store = usePricingStore()
    const statement = await store.fetchUsageStatement('ws_test', '2026-10-01', '2026-10-31')

    expect(statement.total_inferences).toBeGreaterThanOrEqual(0)
  })

  it('estimates cost', async () => {
    const store = usePricingStore()
    const estimate = await store.estimateCost({
      profile_config: {},
      expected_monthly_inferences: 100000
    })

    expect(estimate.total_idr).toBeGreaterThan(0)
    expect(estimate.tax_idr).toBeGreaterThan(0)
  })

  it('clears estimate', () => {
    const store = usePricingStore()
    store.estimate = { subtotal_idr: 1000, tax_idr: 110, total_idr: 1110, breakdown: [] }

    store.clearEstimate()
    expect(store.estimate).toBeNull()
  })
})
