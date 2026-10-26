<template>
  <div class="billing-page">
    <div class="header">
      <h1>Billing & Invoices</h1>
      <div class="header-actions">
        <input v-model="filterStatus" type="text" placeholder="Filter by status..." class="filter-input" />
        <button @click="refreshInvoices" class="btn btn-secondary">Refresh</button>
      </div>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab"
        :class="['tab', { active: activeTab === tab }]"
        @click="activeTab = tab"
      >
        {{ tab }}
      </button>
    </div>

    <div class="tab-content">
      <!-- Invoices Tab -->
      <div v-if="activeTab === 'Invoices'" class="invoices-section">
        <div v-if="pricingStore.loading" class="loading">Loading invoices...</div>
        <div v-if="pricingStore.error" class="error">{{ pricingStore.error }}</div>

        <div v-if="!pricingStore.loading && filteredInvoices.length === 0" class="empty-state">
          <p>No invoices found.</p>
        </div>

        <table v-if="!pricingStore.loading && filteredInvoices.length > 0" class="invoices-table">
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Period</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Due Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="invoice in filteredInvoices" :key="invoice.id">
              <td><strong>{{ invoice.invoice_number }}</strong></td>
              <td>{{ formatDate(invoice.period_start) }} - {{ formatDate(invoice.period_end) }}</td>
              <td>{{ formatIDR(invoice.total_idr) }}</td>
              <td>
                <span :class="['status-badge', `status-${invoice.status.toLowerCase()}`]">
                  {{ invoice.status }}
                </span>
              </td>
              <td>{{ formatDate(invoice.due_date) }}</td>
              <td>
                <button @click="viewInvoiceDetails(invoice)" class="btn btn-sm btn-primary">
                  View
                </button>
                <button @click="downloadInvoicePDF(invoice.invoice_number)" class="btn btn-sm btn-secondary">
                  PDF
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Usage Statement Tab -->
      <div v-if="activeTab === 'Usage'" class="usage-section">
        <div class="usage-filters">
          <div class="filter-group">
            <label>Start Date:</label>
            <input v-model="usageStartDate" type="date" />
          </div>
          <div class="filter-group">
            <label>End Date:</label>
            <input v-model="usageEndDate" type="date" />
          </div>
          <button @click="loadUsageStatement" class="btn btn-primary">Load Statement</button>
        </div>

        <div v-if="pricingStore.loading" class="loading">Loading usage statement...</div>

        <div v-if="pricingStore.usageStatement && !pricingStore.loading" class="usage-details">
          <h3>Usage Summary</h3>
          <div class="summary-cards">
            <div class="card">
              <span class="label">Total Inferences</span>
              <span class="value">{{ pricingStore.usageStatement.total_inferences.toLocaleString() }}</span>
            </div>
            <div class="card">
              <span class="label">Total Cost</span>
              <span class="value">{{ formatIDR(pricingStore.usageStatement.total_cost_idr) }}</span>
            </div>
          </div>

          <h4>Breakdown by Provider</h4>
          <table class="breakdown-table">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Cost (IDR)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(cost, provider) in pricingStore.usageStatement.breakdown_by_provider" :key="provider">
                <td>{{ provider }}</td>
                <td>{{ formatIDR(cost) }}</td>
              </tr>
            </tbody>
          </table>

          <h4>Breakdown by Module</h4>
          <table class="breakdown-table">
            <thead>
              <tr>
                <th>Module</th>
                <th>Cost (IDR)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(cost, module) in pricingStore.usageStatement.breakdown_by_module" :key="module">
                <td>{{ module }}</td>
                <td>{{ formatIDR(cost) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Invoice Details Modal -->
      <div v-if="selectedInvoice" class="modal-overlay" @click="selectedInvoice = null">
        <div class="modal" @click.stop>
          <button class="modal-close" @click="selectedInvoice = null">&times;</button>
          
          <h2>{{ selectedInvoice.invoice_number }}</h2>
          
          <div class="invoice-details">
            <div class="detail-row">
              <span class="label">Period:</span>
              <span>{{ formatDate(selectedInvoice.period_start) }} - {{ formatDate(selectedInvoice.period_end) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Status:</span>
              <span :class="['status-badge', `status-${selectedInvoice.status.toLowerCase()}`]">
                {{ selectedInvoice.status }}
              </span>
            </div>
            <div class="detail-row">
              <span class="label">Due Date:</span>
              <span>{{ formatDate(selectedInvoice.due_date) }}</span>
            </div>
          </div>

          <h4>Line Items</h4>
          <table class="line-items-table">
            <thead>
              <tr>
                <th>Description</th>
                <th>Quantity</th>
                <th>Unit Price</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in selectedInvoice.line_items" :key="index">
                <td>{{ item.description }}</td>
                <td class="text-right">{{ item.quantity }}</td>
                <td class="text-right">{{ formatIDR(item.unit_price) }}</td>
                <td class="text-right">{{ formatIDR(item.amount) }}</td>
              </tr>
            </tbody>
          </table>

          <div class="invoice-summary">
            <div class="summary-row">
              <span>Subtotal:</span>
              <span>{{ formatIDR(selectedInvoice.subtotal_idr) }}</span>
            </div>
            <div class="summary-row">
              <span>Tax (11%):</span>
              <span>{{ formatIDR(selectedInvoice.tax_idr) }}</span>
            </div>
            <div class="summary-row total">
              <span>Total:</span>
              <span>{{ formatIDR(selectedInvoice.total_idr) }}</span>
            </div>
          </div>

          <div class="modal-actions">
            <button @click="downloadInvoicePDF(selectedInvoice.invoice_number)" class="btn btn-primary">
              Download PDF
            </button>
            <button @click="selectedInvoice = null" class="btn btn-secondary">Close</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePricingStore } from '@/stores/pricing'
import { formatIDR, formatDate } from '@/utils/format'
import type { Invoice } from '@/services/api/pricing.types'

const pricingStore = usePricingStore()

const tabs = ['Invoices', 'Usage']
const activeTab = ref('Invoices')
const filterStatus = ref('')
const selectedInvoice = ref<Invoice | null>(null)

const usageStartDate = ref(new Date(new Date().setDate(new Date().getDate() - 30)).toISOString().split('T')[0])
const usageEndDate = ref(new Date().toISOString().split('T')[0])

const filteredInvoices = computed(() => {
  if (!filterStatus.value) return pricingStore.invoices
  return pricingStore.invoices.filter(inv =>
    inv.status.toLowerCase().includes(filterStatus.value.toLowerCase())
  )
})

async function refreshInvoices() {
  await pricingStore.fetchInvoices()
}

function viewInvoiceDetails(invoice: Invoice) {
  selectedInvoice.value = invoice
}

async function downloadInvoicePDF(invoiceNumber: string) {
  try {
    await pricingStore.downloadInvoice(invoiceNumber)
  } catch (err) {
    alert('Failed to download: ' + (err instanceof Error ? err.message : 'Unknown error'))
  }
}

async function loadUsageStatement() {
  try {
    await pricingStore.fetchUsageStatement('ws_default', usageStartDate.value, usageEndDate.value)
  } catch (err) {
    alert('Failed to load usage: ' + (err instanceof Error ? err.message : 'Unknown error'))
  }
}

onMounted(async () => {
  await pricingStore.fetchInvoices()
})
</script>

<style scoped>
.billing-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.filter-input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.tabs {
  display: flex;
  gap: 1rem;
  border-bottom: 2px solid #ddd;
  margin-bottom: 2rem;
}

.tab {
  background: none;
  border: none;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  font-size: 1rem;
  color: #6b7280;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}

.tab.active {
  color: #1f2937;
  border-bottom-color: #3b82f6;
}

.invoices-table {
  width: 100%;
  border-collapse: collapse;
}

.invoices-table th,
.invoices-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.invoices-table th {
  background: #f9fafb;
  font-weight: 600;
}

.invoices-table tbody tr:hover {
  background: #f9fafb;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-draft {
  background: #fef3c7;
  color: #92400e;
}

.status-issued {
  background: #dbeafe;
  color: #1e40af;
}

.status-paid {
  background: #d1fae5;
  color: #065f46;
}

.status-overdue {
  background: #fee2e2;
  color: #991b1b;
}

.status-void {
  background: #e5e7eb;
  color: #374151;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-secondary {
  background: #6b7280;
  color: white;
}

.btn-sm {
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  margin-right: 0.5rem;
}

.usage-filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-group label {
  font-weight: 500;
  font-size: 0.875rem;
}

.filter-group input {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
}

.card .label {
  display: block;
  color: #6b7280;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.card .value {
  display: block;
  font-size: 1.5rem;
  font-weight: bold;
  color: #1f2937;
}

.breakdown-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 2rem;
}

.breakdown-table th,
.breakdown-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.breakdown-table th {
  background: #f9fafb;
  font-weight: 600;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
}

.invoice-details {
  margin-bottom: 2rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.detail-row .label {
  font-weight: 500;
}

.line-items-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 2rem;
}

.line-items-table th,
.line-items-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.line-items-table th {
  background: #f9fafb;
  font-weight: 600;
}

.text-right {
  text-align: right;
}

.invoice-summary {
  background: #f9fafb;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 2rem;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
}

.summary-row.total {
  border-top: 2px solid #e5e7eb;
  padding-top: 1rem;
  margin-top: 1rem;
  font-size: 1.125rem;
  font-weight: bold;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.loading,
.error,
.empty-state {
  padding: 2rem;
  text-align: center;
  background: #f9fafb;
  border-radius: 8px;
}

.error {
  background: #fee2e2;
  color: #991b1b;
}
</style>
