import { DEFAULT_MAP_ZOOM, MAP_MAX_ZOOM, MAP_MIN_ZOOM } from '@src/constants/map'
import plateBoundariesJson from '@src/geo-json/plate-boundaries.json'
import pusgenBandaJson from '@src/geo-json/pusgen-banda.json'
import pusgenJavaJson from '@src/geo-json/pusgen-java.json'
import pusgenKalimantanJson from '@src/geo-json/pusgen-kalimantan.json'
import pusgenMalukuJson from '@src/geo-json/pusgen-maluku.json'
import pusgenSulawesiJson from '@src/geo-json/pusgen-sulawesi.json'
import pusgenSumJson from '@src/geo-json/pusgen-sum.json'
import trenchJson from '@src/geo-json/trench.json'
import volcanoesJson from '@src/geo-json/volcanoes.json'
import { EarthQuakeEvent } from '@src/types/event'
import { Magnitude } from '@src/types/magnitude'
import { Station } from '@src/types/station'
import { WSEvent } from '@src/types/ws-event'
import { Feature, Graticule, Map, MapBrowserEvent, View } from 'ol'
import { OverviewMap } from 'ol/control'
import { easeOut } from 'ol/easing'
import { FeatureLike } from 'ol/Feature'
import GeoJSON from 'ol/format/GeoJSON'
import { Geometry, LineString, Point } from 'ol/geom'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import { unByKey } from 'ol/Observable'
import { fromLonLat, transform } from 'ol/proj'
import { getVectorContext } from 'ol/render'
import RenderEvent from 'ol/render/Event'
import { Cluster, XYZ } from 'ol/source'
import VectorSource from 'ol/source/Vector'
import CircleStyle from 'ol/style/Circle'
import Fill from 'ol/style/Fill'
import RegularShape from 'ol/style/RegularShape'
import Stroke from 'ol/style/Stroke'
import Style, { StyleFunction } from 'ol/style/Style'
import Text from 'ol/style/Text'

import { hexToRGB } from './color'
import { getDepthColor, getMagnitudeWidth } from './event'

const BASE_LAYER = 'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}'
// const BASE_LAYER =
//   'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}'
// const LABEL_LAYER =
//   'https://services.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}'
const ALL_PUSGEN_JSON = [
  pusgenBandaJson,
  pusgenJavaJson,
  pusgenKalimantanJson,
  pusgenMalukuJson,
  pusgenSulawesiJson,
  pusgenSumJson
]

const styles = {
  Volcano: new Style({
    image: new RegularShape({
      points: 3,
      radius: 5,
      fill: new Fill({ color: 'red' }),
      stroke: new Stroke({
        color: 'red',
        width: 1
      }),
      rotation: 0,
      angle: 0
    })
  }),

  TrenchLine: new Style({
    stroke: new Stroke({
      color: 'blue',
      width: 3
    })
  }),

  PlateLine: new Style({
    stroke: new Stroke({
      color: 'green',
      width: 2
    })
  }),

  PusgenLine: new Style({
    stroke: new Stroke({
      color: 'red',
      width: 1
    })
  }),

  Station: new Style({
    image: new RegularShape({
      fill: new Fill({ color: 'green' }),
      points: 6,
      radius: 5,
      stroke: new Stroke({
        color: 'green',
        width: 1
      }),
      rotation: 0,
      angle: 0
    })
  })
}

export const createStationIcon = (text: string, hasPick = false) => {
  return new Style({
    image: new RegularShape({
      points: 6,
      radius: 16,
      fill: new Fill({ color: 'green' }),
      stroke: new Stroke({
        color: hasPick ? 'yellow' : 'green',
        width: 4
      }),
      rotation: 0,
      angle: 0
    }),
    text: new Text({
      text,
      fill: new Fill({
        color: '#fff'
      })
    })
  })
}

export const createVolcanoLayers = () => {
  const vectorSource = new VectorSource({
    features: new GeoJSON().readFeatures(volcanoesJson, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857'
    })
  })

  const volcanoesStyleFunction: StyleFunction = (feature) => {
    const type = feature.getGeometry()?.getType()
    return type === 'Point' ? styles.Volcano : undefined
  }

  const vectorLayer = new VectorLayer({
    source: vectorSource,
    style: volcanoesStyleFunction
  })

  return vectorLayer
}

export const createPlateBoundariesLayers = () => {
  const vectorSource = new VectorSource({
    features: new GeoJSON().readFeatures(plateBoundariesJson, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857'
    })
  })

  const styleFunction: StyleFunction = (feature) => {
    const type = feature.getGeometry()?.getType()
    return type === 'LineString' ? styles.PlateLine : undefined
  }

  const vectorLayer = new VectorLayer({
    source: vectorSource,
    visible: false,
    style: styleFunction
  })

  return vectorLayer
}

export const createTrenchLayers = () => {
  const vectorSource = new VectorSource({
    features: new GeoJSON().readFeatures(trenchJson, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857'
    })
  })

  const styleFunction: StyleFunction = (feature) => {
    const type = feature.getGeometry()?.getType()
    return type === 'LineString' ? styles.TrenchLine : undefined
  }

  const vectorLayer = new VectorLayer({
    source: vectorSource,
    visible: false,
    style: styleFunction
  })

  return vectorLayer
}

export const createPusgenLayers = () => {
  return ALL_PUSGEN_JSON.map((pusgenJSON) => {
    const vectorSource = new VectorSource({
      features: new GeoJSON().readFeatures(pusgenJSON, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857'
      })
    })

    const styleFunction: StyleFunction = (feature) => {
      const type = feature.getGeometry()?.getType()
      return type === 'LineString' ? styles.PusgenLine : undefined
    }

    const vectorLayer = new VectorLayer({
      source: vectorSource,
      visible: false,
      style: styleFunction
    })

    return vectorLayer
  })
}

export const createEventMarker = (event: WSEvent) => {
  const feature = new Feature(new Point(transform([event.longitude, event.latitude], 'EPSG:4326', 'EPSG:3857')))

  feature.setStyle(
    new Style({
      image: new CircleStyle({
        radius: 6,
        stroke: new Stroke({ color: 'red', width: 1 }),
        fill: new Fill({ color: 'rgb(255, 0, 0, 0.5)' })
      })
    })
  )

  feature.setId(event.id)

  return feature
}

export const createStationCluster = (stations: Station[]) => {
  const features = stations.map((station) => {
    const feature = new Feature(new Point(transform([station.longitude, station.latitude], 'EPSG:4326', 'EPSG:3857')))
    feature.setProperties({ station })
    feature.setId(`${station.network}-${station.code}`)
    return feature
  })

  const source = new VectorSource({
    features: features
  })

  const clusterSource = new Cluster({
    distance: 60,
    minDistance: 40,
    source: source
  })

  const styleCache: Record<string, Style> = {}

  const clusters = new VectorLayer({
    source: clusterSource,
    style: function (feature) {
      const childFeatures = feature.get('features') as FeatureLike[]
      const hasPick = childFeatures.some((childFeature) => childFeature.getProperties()?.hasPick ?? false)
      const size = childFeatures.length
      const station = size === 1 ? (childFeatures[0]?.getProperties()?.station as Station) : undefined
      const text = station?.code ?? size.toString()
      const key = `${text}-${hasPick}`

      if (styleCache[key]) {
        return styleCache[key]
      }

      const style = createStationIcon(text, hasPick)

      styleCache[key] = style
      return style
    }
  })

  return { clusters, clusterSource }
}

export const createSelectedEventStationFeatures = (event: EarthQuakeEvent) => {
  const features = event.arrivals.map((arrival) => {
    const station = arrival.station_details
    const latLng = transform([station.longitude, station.latitude], 'EPSG:4326', 'EPSG:3857')
    const feature = new Feature(new Point(latLng))

    feature.setStyle(createStationIcon(station.code))
    return feature
  })
  return features
}

export const createEventStationLine = (event: EarthQuakeEvent) => {
  const eventLatLng = transform([event.longitude, event.latitude], 'EPSG:4326', 'EPSG:3857')
  const features = event.arrivals.map((arrival) => {
    const station = arrival.station_details
    const latLng = transform([station.longitude, station.latitude], 'EPSG:4326', 'EPSG:3857')
    const coordinates = [eventLatLng, latLng]
    const feature = new Feature(new LineString(coordinates))
    return feature
  })
  return features
}

export const createMagnitudeFeature = (event: EarthQuakeEvent, magnitude: Magnitude) => {
  const latLng = transform([event.longitude, event.latitude], 'EPSG:4326', 'EPSG:3857')
  const width = getMagnitudeWidth(magnitude.value)
  const color = getDepthColor(event.depth)
  const feature = new Feature(new Point(latLng))

  feature.setStyle(
    new Style({
      image: new CircleStyle({
        radius: width / 2,
        stroke: new Stroke({ color, width: 1 }),
        fill: new Fill({ color: hexToRGB(color, 0.5) })
      })
    })
  )

  return feature
}

const mapOnPointerMove = (event: MapBrowserEvent<any>, map: Map) => {
  const pixel = map.getEventPixel(event.originalEvent)
  const hit = map.hasFeatureAtPixel(pixel)
  map.getViewport().style.cursor = hit ? 'pointer' : ''
}

export const createOpenLayerMap = (target: HTMLDivElement) => {
  const tileLayer = new TileLayer({ source: new XYZ({ url: BASE_LAYER }) })
  // const labeLayer = new TileLayer({ source: new XYZ({ url: LABEL_LAYER }) })
  const graticuleLayer = new Graticule({
    strokeStyle: new Stroke({
      color: 'rgba(255, 255, 255, 0.4)',
      width: 2,
      lineDash: [0.5, 4]
    }),
    showLabels: true
  })

  const overviewMapControl = new OverviewMap({
    collapsed: false,
    collapsible: false,
    className: 'ol-overviewmap ol-custom-overviewmap top-1 left-1 bg-transparent',
    layers: [
      new TileLayer({
        source: new XYZ({ url: BASE_LAYER })
      })
    ]
  })

  const layers = [tileLayer /*labeLayer*/, graticuleLayer]
  const defaultView = new View({
    center: fromLonLat([118.0149, -2.5489]),
    zoom: DEFAULT_MAP_ZOOM,
    maxZoom: MAP_MAX_ZOOM,
    minZoom: MAP_MIN_ZOOM,
    enableRotation: false
  })

  const map = new Map({
    target,
    layers,
    view: defaultView,
    controls: [overviewMapControl]
  })

  // map.getControls().clear()
  map.on('pointermove', (event) => mapOnPointerMove(event, map))

  return { tileLayer, map }
}

export const flashEventMarker = (feature: Feature<Geometry>, tileLayer: TileLayer<XYZ>, map: Map) => {
  const start = Date.now()
  const duration = 20_000
  const flashGeom = feature.getGeometry()?.clone()

  const listenerKey = tileLayer.on('postrender', animate)

  function animate(event: RenderEvent) {
    const frameState = event.frameState
    if (!flashGeom) return
    if (!frameState) return
    const elapsed = frameState.time - start
    if (elapsed >= duration) {
      unByKey(listenerKey)
      return
    }
    const vectorContext = getVectorContext(event)
    const elapsedRatio = ((elapsed * 16) / duration) % 1
    // radius will be 5 at start and 30 at end.
    const radius = easeOut(elapsedRatio) * 25 + 5
    const opacity = easeOut(1 - elapsedRatio)

    const style = new Style({
      image: new CircleStyle({
        radius: radius,
        stroke: new Stroke({
          color: 'rgba(255, 0, 0, ' + opacity + ')',
          width: 0.25 + opacity
        })
      })
    })

    vectorContext.setStyle(style)
    vectorContext.drawGeometry(flashGeom)
    // tell OpenLayers to continue postrender animation
    map.render()
  }
}
