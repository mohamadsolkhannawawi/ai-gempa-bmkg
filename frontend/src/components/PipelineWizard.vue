<template>
  <div class="pipeline-wizard">
    <div class="wizard-header">
      <h2>Pipeline Configuration Wizard</h2>
      <div class="steps">
        <div
          v-for="(step, index) in steps"
          :key="index"
          :class="['step', { active: currentStep === index, completed: index < currentStep }]"
        >
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-label">{{ step }}</div>
        </div>
      </div>
    </div>

    <div class="wizard-body">
      <!-- Step 1: P-Pick Provider -->
      <div v-if="currentStep === 0" class="step-content">
        <h3>Pilih P-Pick Provider</h3>
        <div class="provider-grid">
          <div
            v-for="provider in pPickProviders"
            :key="provider.id"
            :class="['provider-card', { selected: config.p_pick?.provider === provider.id }]"
            @click="selectPPick(provider)"
          >
            <h4>{{ provider.name }}</h4>
            <p>{{ provider.description }}</p>
            <div class="tiers">
              <label v-for="tier in provider.tiers" :key="tier.name">
                <input
                  type="radio"
                  :name="`p_pick_tier`"
                  :value="tier.name"
                  :checked="config.p_pick?.tier === tier.name"
                  :disabled="!tier.available"
                  @change="selectPPickTier(tier.name)"
                />
                {{ tier.name.toUpperCase() }} - {{ formatIDR(tier.cost_per_inference) }}/inference
                <span v-if="!tier.available">(unavailable)</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 2: Association Provider -->
      <div v-if="currentStep === 1" class="step-content">
        <h3>Pilih Association Provider</h3>
        <div class="provider-grid">
          <div
            v-for="provider in associationProviders"
            :key="provider.id"
            :class="['provider-card', { selected: config.association?.provider === provider.id }]"
            @click="selectAssociation(provider)"
          >
            <h4>{{ provider.name }}</h4>
            <p>{{ provider.description }}</p>
            <div class="tiers">
              <label v-for="tier in provider.tiers" :key="tier.name">
                <input
                  type="radio"
                  :name="`association_tier`"
                  :value="tier.name"
                  :checked="config.association?.tier === tier.name"
                  :disabled="!tier.available"
                  @change="selectAssociationTier(tier.name)"
                />
                {{ tier.name.toUpperCase() }} - {{ formatIDR(tier.cost_per_inference) }}/inference
                <span v-if="!tier.available">(unavailable)</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3: LocMag Provider -->
      <div v-if="currentStep === 2" class="step-content">
        <h3>Pilih Location & Magnitude Provider</h3>
        <div class="provider-grid">
          <div
            v-for="provider in locmagProviders"
            :key="provider.id"
            :class="['provider-card', { selected: config.locmag?.provider === provider.id }]"
            @click="selectLocmag(provider)"
          >
            <h4>{{ provider.name }}</h4>
            <p>{{ provider.description }}</p>
            <div class="tiers">
              <label v-for="tier in provider.tiers" :key="tier.name">
                <input
                  type="radio"
                  :name="`locmag_tier`"
                  :value="tier.name"
                  :checked="config.locmag?.tier === tier.name"
                  :disabled="!tier.available"
                  @change="selectLocmagTier(tier.name)"
                />
                {{ tier.name.toUpperCase() }} - {{ formatIDR(tier.cost_per_inference) }}/inference
                <span v-if="!tier.available">(unavailable)</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4: Review & Save -->
      <div v-if="currentStep === 3" class="step-content">
        <h3>Review Configuration</h3>
        <div class="review-section">
          <div class="config-summary">
            <h4>P-Pick</h4>
            <p><strong>Provider:</strong> {{ config.p_pick?.provider || 'Not selected' }}</p>
            <p><strong>Tier:</strong> {{ config.p_pick?.tier?.toUpperCase() || 'Not selected' }}</p>
          </div>
          <div class="config-summary">
            <h4>Association</h4>
            <p><strong>Provider:</strong> {{ config.association?.provider || 'Not selected' }}</p>
            <p><strong>Tier:</strong> {{ config.association?.tier?.toUpperCase() || 'Not selected' }}</p>
          </div>
          <div class="config-summary">
            <h4>Location & Magnitude</h4>
            <p><strong>Provider:</strong> {{ config.locmag?.provider || 'Not selected' }}</p>
            <p><strong>Tier:</strong> {{ config.locmag?.tier?.toUpperCase() || 'Not selected' }}</p>
          </div>

          <div class="profile-meta">
            <label>
              Profile Name:
              <input v-model="profileName" type="text" placeholder="e.g. Production Pipeline" required />
            </label>
            <label>
              Description (optional):
              <textarea v-model="profileDescription" placeholder="Describe this configuration..." />
            </label>
          </div>
        </div>
      </div>
    </div>

    <div class="wizard-footer">
      <button v-if="currentStep > 0" @click="prevStep" class="btn btn-secondary">Back</button>
      <button v-if="currentStep < 3" @click="nextStep" :disabled="!canProceed" class="btn btn-primary">
        Next
      </button>
      <button v-if="currentStep === 3" @click="saveProfile" :disabled="saving" class="btn btn-success">
        {{ saving ? 'Saving...' : 'Save Profile' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCatalogStore } from '@/stores/catalog'
import { useProfileStore } from '@/stores/profile'
import { useRouter } from 'vue-router'
import { formatIDR } from '@/utils/format'

const catalogStore = useCatalogStore()
const profileStore = useProfileStore()
const router = useRouter()

const steps = ['P-Pick', 'Association', 'LocMag', 'Review']
const currentStep = ref(0)
const saving = ref(false)

const config = ref<{
  p_pick?: { provider: string; tier: string }
  association?: { provider: string; tier: string }
  locmag?: { provider: string; tier: string }
}>({})

const profileName = ref('')
const profileDescription = ref('')

const pPickProviders = computed(() =>
  catalogStore.providers.filter(p => p.module === 'p_pick')
)

const associationProviders = computed(() =>
  catalogStore.providers.filter(p => p.module === 'association')
)

const locmagProviders = computed(() =>
  catalogStore.providers.filter(p => p.module === 'locmag')
)

const canProceed = computed(() => {
  if (currentStep.value === 0) return config.value.p_pick?.provider && config.value.p_pick?.tier
  if (currentStep.value === 1) return config.value.association?.provider && config.value.association?.tier
  if (currentStep.value === 2) return config.value.locmag?.provider && config.value.locmag?.tier
  return true
})

function selectPPick(provider: any) {
  const firstAvailable = provider.tiers.find((t: any) => t.available)
  if (firstAvailable) {
    config.value.p_pick = {
      provider: provider.id,
      tier: firstAvailable.name
    }
  }
}

function selectPPickTier(tier: string) {
  if (config.value.p_pick) {
    config.value.p_pick.tier = tier
  }
}

function selectAssociation(provider: any) {
  const firstAvailable = provider.tiers.find((t: any) => t.available)
  if (firstAvailable) {
    config.value.association = {
      provider: provider.id,
      tier: firstAvailable.name
    }
  }
}

function selectAssociationTier(tier: string) {
  if (config.value.association) {
    config.value.association.tier = tier
  }
}

function selectLocmag(provider: any) {
  const firstAvailable = provider.tiers.find((t: any) => t.available)
  if (firstAvailable) {
    config.value.locmag = {
      provider: provider.id,
      tier: firstAvailable.name
    }
  }
}

function selectLocmagTier(tier: string) {
  if (config.value.locmag) {
    config.value.locmag.tier = tier
  }
}

function nextStep() {
  if (canProceed.value && currentStep.value < 3) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

async function saveProfile() {
  if (!profileName.value.trim()) {
    alert('Profile name required')
    return
  }

  saving.value = true
  try {
    await profileStore.createProfile({
      workspace_id: 'ws_default', // ponytail: hardcoded, get from auth context
      name: profileName.value,
      description: profileDescription.value || undefined,
      config: config.value
    })
    router.push('/pipeline-builder')
  } catch (err) {
    alert('Failed to save profile: ' + (err instanceof Error ? err.message : 'Unknown error'))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await catalogStore.fetchCatalog()
})
</script>

<style scoped>
.pipeline-wizard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.wizard-header {
  margin-bottom: 2rem;
}

.steps {
  display: flex;
  justify-content: space-between;
  margin-top: 1rem;
}

.step {
  flex: 1;
  text-align: center;
  opacity: 0.5;
}

.step.active,
.step.completed {
  opacity: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ddd;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.step.active .step-number {
  background: #3b82f6;
  color: white;
}

.step.completed .step-number {
  background: #10b981;
  color: white;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.provider-card {
  border: 2px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.provider-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

.provider-card.selected {
  border-color: #10b981;
  background: #f0fdf4;
}

.tiers {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-summary {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.profile-meta {
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.profile-meta label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.profile-meta input,
.profile-meta textarea {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.wizard-footer {
  margin-top: 2rem;
  display: flex;
  justify-content: space-between;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-secondary {
  background: #6b7280;
  color: white;
}

.btn-success {
  background: #10b981;
  color: white;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
