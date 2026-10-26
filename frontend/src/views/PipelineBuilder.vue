<template>
  <div class="pipeline-builder">
    <div class="header">
      <h1>Pipeline Builder</h1>
      <button @click="newProfile" class="btn btn-primary">+ New Profile</button>
    </div>

    <div class="content">
      <div class="profiles-list">
        <h2>Saved Profiles</h2>
        <div v-if="profileStore.loading" class="loading">Loading profiles...</div>
        <div v-if="profileStore.error" class="error">{{ profileStore.error }}</div>

        <div v-if="!profileStore.loading && profileStore.profiles.length === 0" class="empty-state">
          <p>No profiles yet. Create one to get started.</p>
        </div>

        <div v-for="profile in profileStore.profiles" :key="profile.id" class="profile-item">
          <div class="profile-info">
            <h3>{{ profile.name }}</h3>
            <p class="description">{{ profile.description || 'No description' }}</p>
            <div class="profile-config">
              <span v-if="profile.config.p_pick" class="badge">
                P-Pick: {{ profile.config.p_pick.provider }}
              </span>
              <span v-if="profile.config.association" class="badge">
                Association: {{ profile.config.association.provider }}
              </span>
              <span v-if="profile.config.locmag" class="badge">
                LocMag: {{ profile.config.locmag.provider }}
              </span>
            </div>
            <p class="meta">
              Updated {{ formatDate(profile.updated_at) }}
              <span v-if="profile.compiled_sha256" class="compiled-badge">✓ Compiled</span>
            </p>
          </div>
          <div class="profile-actions">
            <button @click="editProfile(profile.id)" class="btn btn-sm btn-primary">Edit</button>
            <button @click="viewCost(profile.id)" class="btn btn-sm btn-secondary">Cost</button>
            <button @click="compileProfile(profile.id)" class="btn btn-sm btn-info">
              {{ profile.compiled_sha256 ? 'Recompile' : 'Compile' }}
            </button>
            <button @click="deleteProfile(profile.id)" class="btn btn-sm btn-danger">Delete</button>
          </div>
        </div>
      </div>

      <div class="profile-editor" v-if="selectedProfile">
        <h2>{{ selectedProfile.id ? 'Edit Profile' : 'New Profile' }}</h2>
        
        <div class="form-group">
          <label>Profile Name</label>
          <input v-model="selectedProfile.name" type="text" required />
        </div>

        <div class="form-group">
          <label>Description</label>
          <textarea v-model="selectedProfile.description" rows="3" />
        </div>

        <div class="config-section">
          <h3>Configuration</h3>
          
          <div class="module-config">
            <h4>P-Pick</h4>
            <select v-model="selectedProfile.config.p_pick.provider">
              <option value="">Select provider</option>
              <option v-for="p in pPickProviders" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
            <select v-model="selectedProfile.config.p_pick.tier">
              <option value="">Select tier</option>
              <option value="cpu">CPU</option>
              <option value="gpu">GPU</option>
            </select>
          </div>

          <div class="module-config">
            <h4>Association</h4>
            <select v-model="selectedProfile.config.association.provider">
              <option value="">Select provider</option>
              <option v-for="p in associationProviders" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
            <select v-model="selectedProfile.config.association.tier">
              <option value="">Select tier</option>
              <option value="cpu">CPU</option>
              <option value="gpu">GPU</option>
            </select>
          </div>

          <div class="module-config">
            <h4>Location & Magnitude</h4>
            <select v-model="selectedProfile.config.locmag.provider">
              <option value="">Select provider</option>
              <option v-for="p in locmagProviders" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
            <select v-model="selectedProfile.config.locmag.tier">
              <option value="">Select tier</option>
              <option value="cpu">CPU</option>
              <option value="gpu">GPU</option>
            </select>
          </div>
        </div>

        <div class="price-calculator-section">
          <PriceCalculator :config="selectedProfile.config" />
        </div>

        <div class="form-actions">
          <button @click="saveSelectedProfile" :disabled="profileStore.loading" class="btn btn-success">
            {{ profileStore.loading ? 'Saving...' : 'Save Changes' }}
          </button>
          <button @click="selectedProfile = null" class="btn btn-secondary">Cancel</button>
        </div>
      </div>

      <div v-if="costEstimate" class="cost-breakdown">
        <h2>Cost Estimate</h2>
        <div class="estimate-detail">
          <p><strong>Monthly Estimate:</strong> {{ formatIDR(costEstimate.monthly_estimate) }}</p>
          <div class="breakdown-table">
            <div v-for="item in costEstimate.breakdown" :key="item.module" class="breakdown-row">
              <span>{{ item.module }} ({{ item.provider }})</span>
              <span>{{ formatIDR(item.cost_per_inference) }}/inference</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProfileStore } from '@/stores/profile'
import { useCatalogStore } from '@/stores/catalog'
import { formatDate, formatIDR } from '@/utils/format'
import PriceCalculator from '@/components/PriceCalculator.vue'
import type { Profile } from '@/services/api/profile.types'

const profileStore = useProfileStore()
const catalogStore = useCatalogStore()

const selectedProfile = ref<Partial<Profile> | null>(null)
const costEstimate = ref(null)

const pPickProviders = computed(() =>
  catalogStore.providers.filter(p => p.module === 'p_pick')
)

const associationProviders = computed(() =>
  catalogStore.providers.filter(p => p.module === 'association')
)

const locmagProviders = computed(() =>
  catalogStore.providers.filter(p => p.module === 'locmag')
)

function newProfile() {
  selectedProfile.value = {
    name: '',
    description: '',
    config: {
      p_pick: { provider: '', tier: 'cpu' },
      association: { provider: '', tier: 'cpu' },
      locmag: { provider: '', tier: 'cpu' }
    }
  }
}

function editProfile(id: string) {
  const profile = profileStore.profiles.find(p => p.id === id)
  if (profile) {
    selectedProfile.value = { ...profile }
  }
}

async function saveSelectedProfile() {
  if (!selectedProfile.value) return

  try {
    if (selectedProfile.value.id) {
      await profileStore.updateProfile(selectedProfile.value.id as string, selectedProfile.value)
    } else {
      await profileStore.createProfile({
        workspace_id: 'ws_default',
        name: selectedProfile.value.name!,
        description: selectedProfile.value.description,
        config: selectedProfile.value.config!
      })
    }
    selectedProfile.value = null
  } catch (err) {
    alert('Failed to save: ' + (err instanceof Error ? err.message : 'Unknown error'))
  }
}

async function deleteProfile(id: string) {
  if (confirm('Delete this profile?')) {
    try {
      await profileStore.deleteProfile(id)
    } catch (err) {
      alert('Failed to delete: ' + (err instanceof Error ? err.message : 'Unknown error'))
    }
  }
}

async function compileProfile(id: string) {
  try {
    await profileStore.compileProfile(id, {})
    alert('Profile compiled successfully')
  } catch (err) {
    alert('Failed to compile: ' + (err instanceof Error ? err.message : 'Unknown error'))
  }
}

async function viewCost(id: string) {
  try {
    const estimate = await profileStore.estimateCost(id)
    costEstimate.value = estimate
  } catch (err) {
    alert('Failed to get cost estimate: ' + (err instanceof Error ? err.message : 'Unknown error'))
  }
}

onMounted(async () => {
  await profileStore.fetchProfiles()
  await catalogStore.fetchCatalog()
})
</script>

<style scoped>
.pipeline-builder {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.profiles-list {
  border-right: 1px solid #ddd;
  padding-right: 2rem;
}

.profile-item {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: start;
}

.profile-info {
  flex: 1;
}

.profile-info h3 {
  margin: 0 0 0.5rem 0;
}

.description {
  color: #6b7280;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.badge {
  display: inline-block;
  background: #dbeafe;
  color: #1e40af;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  margin-right: 0.5rem;
  margin-bottom: 0.5rem;
}

.meta {
  font-size: 0.75rem;
  color: #9ca3af;
}

.compiled-badge {
  color: #10b981;
  font-weight: bold;
}

.profile-actions {
  display: flex;
  gap: 0.5rem;
  flex-direction: column;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
}

.config-section {
  margin: 2rem 0;
}

.module-config {
  margin-bottom: 1rem;
}

.module-config select {
  display: block;
  margin-top: 0.5rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
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

.btn-info {
  background: #06b6d4;
  color: white;
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading,
.error,
.empty-state {
  padding: 1rem;
  text-align: center;
}

.error {
  background: #fee2e2;
  color: #991b1b;
  border-radius: 4px;
}

.cost-breakdown {
  margin-top: 2rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
}

.estimate-detail {
  margin-top: 1rem;
}

.breakdown-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #eee;
}
</style>
