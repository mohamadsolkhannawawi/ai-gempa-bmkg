<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { toast } from 'vue3-toastify'
import axios from 'axios'
import { API_BASE_URL } from '@src/constants/env'
import { ConfigLayout } from '../config-layout'

interface ModelCatalog {
  id: string
  name: string
  description: string
  stage: 'p_pick' | 'association' | 'locmag'
  tier: string
  supported_channels?: string[]
  min_sample_rate?: number
  status: string
  tags: string[]
}

interface PipelineConfig {
  name: string
  description: string
  p_pick: { provider: string; tier: string }
  association: { provider: string; tier: string }
  locmag: { provider: string; tier: string }
  is_active: boolean
  compiled_sha256?: string
  updated_at?: string
}

const catalog = ref<ModelCatalog[]>([])
const loading = ref(true)
const saving = ref(false)
const compiling = ref(false)

const currentConfig = ref<PipelineConfig>({
  name: 'Default BMKG Operational Pipeline',
  description: 'Standard operational earthquake detection pipeline',
  p_pick: { provider: 'sta_lta', tier: 'CPU' },
  association: { provider: 'dbscan', tier: 'CPU' },
  locmag: { provider: 'geiger', tier: 'CPU' },
  is_active: true,
  compiled_sha256: '8f4e2a1b9c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f'
})

// Filtered models per stage
const pPickModels = computed(() => catalog.value.filter((m) => m.stage === 'p_pick'))
const assocModels = computed(() => catalog.value.filter((m) => m.stage === 'association'))
const locMagModels = computed(() => catalog.value.filter((m) => m.stage === 'locmag'))

// Selected model objects for detail display
const selectedPPick = computed(() =>
  catalog.value.find((m) => m.id === currentConfig.value.p_pick.provider)
)
const selectedAssoc = computed(() =>
  catalog.value.find((m) => m.id === currentConfig.value.association.provider)
)
const selectedLocMag = computed(() =>
  catalog.value.find((m) => m.id === currentConfig.value.locmag.provider)
)

const apiUrl = computed(() => {
  return API_BASE_URL || 'http://localhost:38003/api/v1'
})

onMounted(async () => {
  await fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    // 1. Fetch catalog
    const catalogRes = await axios.get(`${apiUrl.value}/pipeline/catalog`)
    if (catalogRes.data?.data) {
      catalog.value = catalogRes.data.data
    }

    // 2. Fetch current active configuration
    const configRes = await axios.get(`${apiUrl.value}/pipeline/config`)
    if (configRes.data?.data) {
      currentConfig.value = configRes.data.data
    }
  } catch (err: any) {
    console.warn('Menggunakan fallback data katalog default:', err)
    // Fallback default catalog jika offline
    catalog.value = [
      {
        id: 'sta_lta',
        name: 'STA/LTA P-Pick',
        description: 'Short-Term Average / Long-Term Average — klasik, real-time CPU picking',
        stage: 'p_pick',
        tier: 'CPU',
        supported_channels: ['BHZ', 'HHZ', 'SHZ'],
        min_sample_rate: 20,
        status: 'active',
        tags: ['classic', 'cpu', 'real-time', 'robust']
      },
      {
        id: 'phasenet',
        name: 'PhaseNet P-Pick',
        description: 'Deep-learning picker (CNN-based), GPU-accelerated, high recall',
        stage: 'p_pick',
        tier: 'GPU_BASIC',
        supported_channels: ['BHZ', 'HHZ'],
        min_sample_rate: 40,
        status: 'active',
        tags: ['deep-learning', 'gpu', 'high-recall', 'cnn']
      },
      {
        id: 'eqtransformer',
        name: 'EQ-Transformer P-Pick',
        description: 'Transformer-based picker, multi-station, long-range detection',
        stage: 'p_pick',
        tier: 'GPU_BASIC',
        supported_channels: ['BHZ', 'HHZ'],
        min_sample_rate: 40,
        status: 'active',
        tags: ['transformer', 'gpu', 'attention', 'long-range']
      },
      {
        id: 'dbscan',
        name: 'DBSCAN Phase Association',
        description: 'Density-based spatial clustering for seismic phase association',
        stage: 'association',
        tier: 'CPU',
        status: 'active',
        tags: ['clustering', 'cpu', 'real-time']
      },
      {
        id: 'gamma',
        name: 'GaMMA Gaussian Mixture Association',
        description: 'Gaussian Mixture Model association with probabilistic travel-time clustering',
        stage: 'association',
        tier: 'GPU_BASIC',
        status: 'active',
        tags: ['probabilistic', 'gpu', 'gmm']
      },
      {
        id: 'pyocto',
        name: 'PyOcto Fast Octree Association',
        description: 'Octree-based high-throughput association for dense regional networks',
        stage: 'association',
        tier: 'CPU',
        status: 'active',
        tags: ['octree', 'cpu', 'high-throughput']
      },
      {
        id: 'geiger',
        name: 'Geiger 1D Earthquake Location',
        description: 'Classical linearized iterative inversion with 1D velocity model',
        stage: 'locmag',
        tier: 'CPU',
        status: 'active',
        tags: ['classic', 'cpu', 'inversion', '1d-model']
      },
      {
        id: 'nonlinloc',
        name: 'NonLinLoc 3D Probabilistic Location',
        description: 'Non-linear global search probabilistic location with 3D velocity models',
        stage: 'locmag',
        tier: 'CPU',
        status: 'active',
        tags: ['probabilistic', 'cpu', '3d-model', 'grid-search']
      }
    ]
  } finally {
    loading.value = false
  }
}

async function handleCompile() {
  compiling.value = true
  try {
    const res = await axios.post(`${apiUrl.value}/pipeline/compile`, {
      p_pick: currentConfig.value.p_pick,
      association: currentConfig.value.association,
      locmag: currentConfig.value.locmag
    })
    if (res.data?.sha256) {
      currentConfig.value.compiled_sha256 = res.data.sha256
      toast.success(`Pipeline valid! SHA256: ${res.data.sha256.substring(0, 12)}...`)
    }
  } catch (err: any) {
    toast.error('Kompilasi pipeline gagal: ' + (err.response?.data?.detail || err.message))
  } finally {
    compiling.value = false
  }
}

async function handleSaveConfig() {
  saving.value = true
  try {
    const res = await axios.post(`${apiUrl.value}/pipeline/config`, currentConfig.value)
    if (res.data?.data) {
      currentConfig.value = res.data.data
      toast.success('Konfigurasi AI Pipeline berhasil disimpan dan diaktifkan!')
    }
  } catch (err: any) {
    toast.error('Gagal menyimpan konfigurasi: ' + (err.response?.data?.detail || err.message))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ConfigLayout>
    <div class="p-6 max-w-7xl mx-auto space-y-6">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-base-content/10 pb-6">
        <div>
          <div class="flex items-center gap-3">
            <h1 class="text-2xl font-bold tracking-tight text-base-content">
              AI Pipeline Architecture Configuration
            </h1>
            <span class="badge badge-success gap-1 font-semibold text-xs py-2 px-3">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Active Profile
            </span>
          </div>
          <p class="text-sm text-base-content/70 mt-1">
            Konfigurasi arsitektur microservices AI pendeteksi gempa BMKG AI-TEWS secara dinamis.
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            class="btn btn-outline btn-sm gap-2"
            :disabled="compiling"
            @click="handleCompile"
          >
            <span v-if="compiling" class="loading loading-spinner loading-xs"></span>
            ✓ Validasi & Kompilasi
          </button>
          <button
            class="btn btn-primary btn-sm gap-2"
            :disabled="saving"
            @click="handleSaveConfig"
          >
            <span v-if="saving" class="loading loading-spinner loading-xs"></span>
            Simpan & Terapkan Arsitektur
          </button>
        </div>
      </div>

      <!-- Info Profile Metadata -->
      <div class="bg-base-200/60 rounded-xl p-4 border border-base-content/10 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="text-xs font-semibold uppercase text-base-content/60 tracking-wider">Nama Profil</label>
          <input
            v-model="currentConfig.name"
            type="text"
            class="input input-sm input-bordered w-full mt-1 bg-base-100"
          />
        </div>
        <div>
          <label class="text-xs font-semibold uppercase text-base-content/60 tracking-wider">Deskripsi Operasional</label>
          <input
            v-model="currentConfig.description"
            type="text"
            class="input input-sm input-bordered w-full mt-1 bg-base-100"
          />
        </div>
        <div>
          <label class="text-xs font-semibold uppercase text-base-content/60 tracking-wider">Compiled Hash (SHA256)</label>
          <div class="text-xs font-mono bg-base-300 py-2 px-3 rounded-lg truncate mt-1 text-emerald-400 border border-base-content/5">
            {{ currentConfig.compiled_sha256 || 'Belum terkompilasi' }}
          </div>
        </div>
      </div>

      <!-- Pipeline Flow Path Visualization -->
      <div class="bg-base-200/40 rounded-xl p-4 border border-base-content/10">
        <div class="text-xs font-semibold uppercase text-base-content/60 tracking-wider mb-3">
          Alur Pipeline Saat Ini (End-to-End Inference Flow)
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex items-center gap-2 bg-base-100 px-4 py-2 rounded-lg border border-primary/30 shadow-sm">
            <span class="text-xs font-bold text-primary">1. P-PICK</span>
            <span class="font-medium text-sm">{{ selectedPPick?.name || currentConfig.p_pick.provider }}</span>
            <span class="badge badge-xs" :class="currentConfig.p_pick.tier === 'GPU_BASIC' ? 'badge-warning' : 'badge-neutral'">
              {{ currentConfig.p_pick.tier }}
            </span>
          </div>

          <span class="text-base-content/40 font-bold">➔</span>

          <div class="flex items-center gap-2 bg-base-100 px-4 py-2 rounded-lg border border-secondary/30 shadow-sm">
            <span class="text-xs font-bold text-secondary">2. ASSOCIATION</span>
            <span class="font-medium text-sm">{{ selectedAssoc?.name || currentConfig.association.provider }}</span>
            <span class="badge badge-xs" :class="currentConfig.association.tier === 'GPU_BASIC' ? 'badge-warning' : 'badge-neutral'">
              {{ currentConfig.association.tier }}
            </span>
          </div>

          <span class="text-base-content/40 font-bold">➔</span>

          <div class="flex items-center gap-2 bg-base-100 px-4 py-2 rounded-lg border border-accent/30 shadow-sm">
            <span class="text-xs font-bold text-accent">3. LOCMAG</span>
            <span class="font-medium text-sm">{{ selectedLocMag?.name || currentConfig.locmag.provider }}</span>
            <span class="badge badge-xs badge-neutral">
              {{ currentConfig.locmag.tier }}
            </span>
          </div>
        </div>
      </div>

      <!-- 3 Stage Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- STAGE 1: P-PICK -->
        <div class="card bg-base-200 border border-base-content/10 shadow-sm hover:border-primary/50 transition-colors">
          <div class="card-body p-5 space-y-4">
            <div class="flex items-center justify-between border-b border-base-content/10 pb-3">
              <div>
                <span class="text-xs font-bold text-primary uppercase tracking-wider">Stage 1</span>
                <h2 class="card-title text-base font-bold">Phase Picking (P-Pick)</h2>
              </div>
              <div class="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold text-sm">
                01
              </div>
            </div>

            <div class="form-control w-full">
              <label class="label py-1">
                <span class="label-text text-xs font-semibold">Pilih Model AI Picker</span>
              </label>
              <select
                v-model="currentConfig.p_pick.provider"
                class="select select-bordered select-sm w-full bg-base-100"
              >
                <option v-for="m in pPickModels" :key="m.id" :value="m.id">
                  {{ m.name }} ({{ m.tier }})
                </option>
              </select>
            </div>

            <div class="form-control w-full">
              <label class="label py-1">
                <span class="label-text text-xs font-semibold">Compute Tier</span>
              </label>
              <select
                v-model="currentConfig.p_pick.tier"
                class="select select-bordered select-sm w-full bg-base-100"
              >
                <option value="CPU">CPU Mode (Standard)</option>
                <option value="GPU_BASIC">GPU Acceleration (NVIDIA CUDA)</option>
              </select>
            </div>

            <!-- Detail box -->
            <div v-if="selectedPPick" class="bg-base-300/50 rounded-lg p-3 text-xs space-y-2 border border-base-content/5">
              <p class="text-base-content/80">{{ selectedPPick.description }}</p>
              <div class="flex flex-wrap gap-1 pt-1">
                <span v-for="tag in selectedPPick.tags" :key="tag" class="badge badge-outline badge-xs text-base-content/60">
                  #{{ tag }}
                </span>
              </div>
              <div class="text-[11px] text-base-content/60 pt-1 border-t border-base-content/5">
                Kanal: {{ selectedPPick.supported_channels?.join(', ') || 'Semua' }} | Min Freq: {{ selectedPPick.min_sample_rate || 20 }} Hz
              </div>
            </div>
          </div>
        </div>

        <!-- STAGE 2: ASSOCIATION -->
        <div class="card bg-base-200 border border-base-content/10 shadow-sm hover:border-secondary/50 transition-colors">
          <div class="card-body p-5 space-y-4">
            <div class="flex items-center justify-between border-b border-base-content/10 pb-3">
              <div>
                <span class="text-xs font-bold text-secondary uppercase tracking-wider">Stage 2</span>
                <h2 class="card-title text-base font-bold">Phase Association</h2>
              </div>
              <div class="w-8 h-8 rounded-lg bg-secondary/10 text-secondary flex items-center justify-center font-bold text-sm">
                02
              </div>
            </div>

            <div class="form-control w-full">
              <label class="label py-1">
                <span class="label-text text-xs font-semibold">Pilih Model Associator</span>
              </label>
              <select
                v-model="currentConfig.association.provider"
                class="select select-bordered select-sm w-full bg-base-100"
              >
                <option v-for="m in assocModels" :key="m.id" :value="m.id">
                  {{ m.name }} ({{ m.tier }})
                </option>
              </select>
            </div>

            <div class="form-control w-full">
              <label class="label py-1">
                <span class="label-text text-xs font-semibold">Compute Tier</span>
              </label>
              <select
                v-model="currentConfig.association.tier"
                class="select select-bordered select-sm w-full bg-base-100"
              >
                <option value="CPU">CPU Mode (Standard)</option>
                <option value="GPU_BASIC">GPU Acceleration (NVIDIA CUDA)</option>
              </select>
            </div>

            <!-- Detail box -->
            <div v-if="selectedAssoc" class="bg-base-300/50 rounded-lg p-3 text-xs space-y-2 border border-base-content/5">
              <p class="text-base-content/80">{{ selectedAssoc.description }}</p>
              <div class="flex flex-wrap gap-1 pt-1">
                <span v-for="tag in selectedAssoc.tags" :key="tag" class="badge badge-outline badge-xs text-base-content/60">
                  #{{ tag }}
                </span>
              </div>
              <div class="text-[11px] text-base-content/60 pt-1 border-t border-base-content/5">
                Metode: {{ selectedAssoc.name }} | Multi-Station Cluster
              </div>
            </div>
          </div>
        </div>

        <!-- STAGE 3: LOCMAG -->
        <div class="card bg-base-200 border border-base-content/10 shadow-sm hover:border-accent/50 transition-colors">
          <div class="card-body p-5 space-y-4">
            <div class="flex items-center justify-between border-b border-base-content/10 pb-3">
              <div>
                <span class="text-xs font-bold text-accent uppercase tracking-wider">Stage 3</span>
                <h2 class="card-title text-base font-bold">Location & Magnitude</h2>
              </div>
              <div class="w-8 h-8 rounded-lg bg-accent/10 text-accent flex items-center justify-center font-bold text-sm">
                03
              </div>
            </div>

            <div class="form-control w-full">
              <label class="label py-1">
                <span class="label-text text-xs font-semibold">Pilih Model Inversi Hiposenter</span>
              </label>
              <select
                v-model="currentConfig.locmag.provider"
                class="select select-bordered select-sm w-full bg-base-100"
              >
                <option v-for="m in locMagModels" :key="m.id" :value="m.id">
                  {{ m.name }} ({{ m.tier }})
                </option>
              </select>
            </div>

            <div class="form-control w-full">
              <label class="label py-1">
                <span class="label-text text-xs font-semibold">Compute Tier</span>
              </label>
              <select
                v-model="currentConfig.locmag.tier"
                class="select select-bordered select-sm w-full bg-base-100"
              >
                <option value="CPU">CPU Mode (Standard)</option>
              </select>
            </div>

            <!-- Detail box -->
            <div v-if="selectedLocMag" class="bg-base-300/50 rounded-lg p-3 text-xs space-y-2 border border-base-content/5">
              <p class="text-base-content/80">{{ selectedLocMag.description }}</p>
              <div class="flex flex-wrap gap-1 pt-1">
                <span v-for="tag in selectedLocMag.tags" :key="tag" class="badge badge-outline badge-xs text-base-content/60">
                  #{{ tag }}
                </span>
              </div>
              <div class="text-[11px] text-base-content/60 pt-1 border-t border-base-content/5">
                Model Kecepatan: 1D AK135 / 3D CRUST1.0 Regional BMKG
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </ConfigLayout>
</template>
