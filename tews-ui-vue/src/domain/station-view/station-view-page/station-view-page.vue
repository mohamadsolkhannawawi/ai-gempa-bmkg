<script setup lang="ts">
import { OLMap } from '@src/components/ol-map'
import useGetStationList from '@src/hooks/use-get-station-list'
import usePickingSocket from '@src/hooks/use-picking-socket'
import { Station } from '@src/types/station'
import { WebsocketPickingResponse } from '@src/types/waveform'
import { createStationCluster } from '@src/utils/ol-map'
import { useToggle } from '@vueuse/core'
import { addSeconds, isAfter } from 'date-fns'
import { Feature, Map, MapBrowserEvent } from 'ol'
import { FeatureLike } from 'ol/Feature'
import { Geometry, Point } from 'ol/geom'
import VectorLayer from 'ol/layer/Vector'
import { Cluster } from 'ol/source'
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ConfigIcons } from '../config-icons'
import { SelectedStationClusterDrawer } from '../selected-station-cluster-drawer'
import { SelectedStationDrawer } from '../selected-station-drawer'

const map = ref<Map | null>(null)
const selectedStation = ref<Station | null>(null)
const selectedStations = ref<Station[] | null>(null)
const clusterLayer = ref<VectorLayer<Feature<Geometry>> | null>(null)
const clusterSource = ref<Cluster<Feature<Point>> | null>(null)
const [isSettingOpen, toggleSettingOpen] = useToggle()
const router = useRouter()
const pickStations = ref<Record<string, Date>>({})
const interval = ref<number | null>(null)

usePickingSocket((newPick) => handleNewPick(newPick))
const { refetch: fetchStations } = useGetStationList(true)

const blinkState: Record<string, number> = {}

const closeSelectedStationDrawer = () => {
  selectedStation.value = null
}

const closeSelectedStationClusteDrawer = () => {
  selectedStations.value = null
}

const onSelectStation = (station: Station) => {
  selectedStation.value = station
}

const onSelectCluster = (stations: Station[]) => {
  selectedStations.value = stations
}

const navigateToWaveform = () => {
  router.push('/trace-view')
}

const renderStations = async (mapCanvas: Map) => {
  const { data } = await fetchStations()
  const stations = data?.data ?? []

  const createdCluster = createStationCluster(stations)

  mapCanvas.addLayer(createdCluster.clusters)

  clusterLayer.value = createdCluster.clusters
  clusterSource.value = createdCluster.clusterSource
}

const onMapCreated = (mapCanvas: Map) => {
  map.value = mapCanvas
  renderStations(mapCanvas)
}

const onMapClick = (event: MapBrowserEvent<any>) => {
  if (!clusterLayer.value) return

  const clusters = clusterLayer.value

  clusters.getFeatures(event.pixel).then((clickedFeatures) => {
    if (!clickedFeatures.length) return

    const features = clickedFeatures[0].get('features') as FeatureLike[]
    const stations = features.map((feature) => feature.getProperties()?.station as Station | undefined)
    const isStationMarkers = stations.every((station) => !!station)

    if (!isStationMarkers) return
    if (!stations.length) return

    if (stations.length > 1) {
      setTimeout(() => {
        onSelectCluster(stations)
      }, 100)
    } else {
      onSelectStation(stations[0])
    }
  })
}

const removeBlinkFromFeature = (fullStationName: string, feature: Feature<Point>) => {
  if (blinkState[fullStationName]) {
    clearInterval(blinkState[fullStationName])
  }

  feature.setProperties({ hasPick: false })
}

const addBlinkToFeature = (fullStationName: string, feature: Feature<Point>) => {
  if (blinkState[fullStationName]) {
    clearInterval(blinkState[fullStationName])

    const stationList = document.querySelector(`#${fullStationName}`)
    stationList?.classList.remove('has-pick')
  }

  blinkState[fullStationName] = setInterval(() => {
    const hasPick = feature.getProperties()?.hasPick ?? false
    feature.setProperties({ hasPick: !hasPick })

    const stationList = document.querySelector(`#${fullStationName}`)
    if (hasPick) {
      stationList?.classList.add('has-pick')
    } else {
      stationList?.classList.remove('has-pick')
    }
  }, 1000)
}

const getFeatureByStationName = (fullStationName: string) => {
  if (!clusterSource.value) return

  const features = clusterSource.value.getFeatures()

  for (const feature of features) {
    const childFeatures = (feature.getProperties()?.features as Feature<Point>[]) ?? []
    for (const childFeature of childFeatures) {
      if (childFeature.getId() === fullStationName) {
        return childFeature
      }
    }
  }

  return null
}

const handleNewPick = ({ station, network }: WebsocketPickingResponse) => {
  const fullStationName = `${network}-${station}`

  pickStations.value = {
    ...pickStations.value,
    [fullStationName]: addSeconds(new Date(), 30)
  }

  const feature = getFeatureByStationName(fullStationName)

  if (feature) {
    addBlinkToFeature(fullStationName, feature)
  }
}

const checkPickExpiration = () => {
  let hasDeletedPick = false
  const newPicksStations = { ...pickStations.value }
  for (const stationName of Object.keys(newPicksStations)) {
    if (isAfter(new Date(), newPicksStations[stationName])) {
      delete newPicksStations[stationName]
      const feature = getFeatureByStationName(stationName)
      if (feature) {
        removeBlinkFromFeature(stationName, feature)
      }
      hasDeletedPick = true
    }
  }

  if (hasDeletedPick) {
    pickStations.value = newPicksStations
  }
}

onMounted(() => {
  interval.value = setInterval(() => {
    checkPickExpiration()
  }, 10_000)
})

onUnmounted(() => {
  if (interval.value) {
    clearInterval(interval.value)
  }
})
</script>

<template>
  <div class="w-full h-full relative">
    <OLMap
      :is-settings-open="isSettingOpen"
      @map-created="onMapCreated"
      @map-click="onMapClick"
      @close-settings="toggleSettingOpen" />

    <div class="absolute bottom-1 left-1 z-[999]">
      <ConfigIcons @open-settings="toggleSettingOpen" @open-waveform="navigateToWaveform" />
    </div>
  </div>

  <SelectedStationDrawer v-if="selectedStation" :station="selectedStation" @close="closeSelectedStationDrawer" />

  <SelectedStationClusterDrawer
    v-if="selectedStations"
    :stations="selectedStations"
    @select-channel="onSelectStation"
    @close="closeSelectedStationClusteDrawer" />
</template>
