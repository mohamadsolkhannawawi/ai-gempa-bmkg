import plateBoundariesJson from '../../geo-json/plate-boundaries.json'
import trenchJson from '../../geo-json/trench.json'
import volcanoesJson from '../../geo-json/volcanoes.json'
import L from 'leaflet'

const volcanoIcon = L.icon({
  iconUrl: '/images/volcano.svg',
  iconSize: [12, 9]
})

export const createTrenchMarker = () => {
  // @ts-expect-error
  return L.geoJSON(trenchJson, {
    style: {
      color: '#000000',
      weight: 4,
      opacity: 1
    },
    interactive: false
  })
}

export const createPusgenMarker = (pusgenJson: any) => {
  return L.geoJSON(pusgenJson, {
    style: {
      color: '#ff5861',
      weight: 1,
      opacity: 0.8
    },
    interactive: false
  })
}

export const createPlateBoundariesMarker = () => {
  // @ts-expect-error
  return L.geoJSON(plateBoundariesJson, {
    style: {
      color: '#333333',
      weight: 2,
      opacity: 0.8
    },
    interactive: false
  })
}

export const createVolcanoMarkers = () =>
  // @ts-ignore
  L.geoJSON(volcanoesJson, {
    pointToLayer: function (feature, latlng) {
      return L.marker(latlng, {
        title: 'Volcano',
        alt: 'Volcano',
        icon: volcanoIcon,
        interactive: false
      })
    }
  })
