<template>
  <div class="price-calculator">
    <h3>Cost Estimator</h3>
    
    <div class="input-group">
      <label>Expected Monthly Inferences:</label>
      <input
        v-model.number="monthlyInferences"
        type="number"
        min="0"
        step="1000"
        placeholder="e.g. 100000"
      />
    </div>

    <div v-if="loading" class="loading">Calculating...</div>

    <div v-if="estimate && !loading" class="estimate-result">
      <div class="total">
        <h4>Estimated Monthly Cost</h4>
        <p class="amount">{{ formatIDR(estimate.total_idr) }}</p>
        <p class="breakdown-label">
          Subtotal: {{ formatIDR(estimate.subtotal_idr) }}<br/>
          Tax (11%): {{ formatIDR(estimate.tax_idr) }}
        </p>
      </div>

      <div class="breakdown">
        <h5>Breakdown by Module</h5>
        <div v-for="item in estimate.breakdown" :key="item.module" class="breakdown-item">
          <span>{{ item.module }} ({{ item.provider }})</span>
          <span>{{ formatIDR(item.cost_idr) }}</span>
        </div>
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePricingStore } from '@/stores/pricing'
import { formatIDR } from '@/utils/format'
import { useDebounce } from '@/composables/useDebounce'

interface Props {
  config: {
    p_pick?: { provider: string; tier: string }
    association?: { provider: string; tier: string }
    locmag?: { provider: string; tier: string }
  }
}

const props = defineProps<Props>()

const pricingStore = usePricingStore()
const monthlyInferences = ref(100000)
const loading = ref(false)
const error = ref<string | null>(null)

const estimate = ref(pricingStore.estimate)

const debouncedInferences = useDebounce(monthlyInferences, 500)

watch([debouncedInferences, () => props.config], async () => {
  if (!props.config.p_pick && !props.config.association && !props.config.locmag) {
    estimate.value = null
    return
  }

  if (monthlyInferences.value <= 0) {
    estimate.value = null
    return
  }

  loading.value = true
  error.value = null

  try {
    const result = await pricingStore.estimateCost({
      profile_config: props.config,
      expected_monthly_inferences: monthlyInferences.value
    })
    estimate.value = result
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to estimate cost'
  } finally {
    loading.value = false
  }
}, { deep: true })
</script>

<style scoped>
.price-calculator {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  background: #f9fafb;
}

.input-group {
  margin-bottom: 1rem;
}

.input-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.input-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.loading {
  text-align: center;
  color: #6b7280;
  padding: 1rem;
}

.estimate-result {
  margin-top: 1rem;
}

.total {
  background: #fff;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  text-align: center;
}

.amount {
  font-size: 2rem;
  font-weight: bold;
  color: #10b981;
  margin: 0.5rem 0;
}

.breakdown-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.breakdown h5 {
  margin-bottom: 0.5rem;
}

.breakdown-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.error {
  color: #ef4444;
  padding: 1rem;
  background: #fee2e2;
  border-radius: 4px;
  margin-top: 1rem;
}
</style>
