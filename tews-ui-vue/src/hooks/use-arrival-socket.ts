import { SOCKET_BASE_URL } from '@src/constants/env'
import { RealtimeArrival, WebsocketArrivalResponse } from '@src/types/waveform'
import { onMounted, onUnmounted, ref } from 'vue'

function useArrivalSocket() {
  const pickingWebSocket = ref<WebSocket | null>(null)
  const timeout = ref<number | null>(null)
  const reconnectTimeout = ref<number | null>(null)
  const reconnectCount = ref(0)

  const handleArrivalData = ({ network, station, picks, pick_source_id }: WebsocketArrivalResponse) => {
    if (!window.socketData) {
      window.socketData = {}
    }

    if (!network || !station || !picks) {
      return
    }

    const channelName = `${network}.${station}`

    if (!window.socketData[channelName]) {
      window.socketData[channelName] = {
        picks: {},
        arrivals: {}
      }
    }

    delete window.socketData[channelName].picks[pick_source_id]

    for (const pick of picks) {
      const realtimeArrival: RealtimeArrival = {
        _id: pick._id,
        pick_source_id,
        station,
        timestamp: pick.timestamp,
        phase_type: pick.type
      }

      if (!window.socketData[channelName].arrivals[pick_source_id]) {
        window.socketData[channelName].arrivals[pick_source_id] = [realtimeArrival]
      } else {
        window.socketData[channelName].arrivals[pick_source_id].push(realtimeArrival)
      }
    }
  }

  const parseArrivalPickData = (data: string) => {
    try {
      const parsedData = JSON.parse(data) as WebsocketArrivalResponse
      return parsedData
    } catch (e) {
      console.error(e)
      return null
    }
  }

  const resetTimeout = () => {
    if (timeout.value) {
      clearTimeout(timeout.value)
      timeout.value = null
    }
    if (reconnectTimeout.value) {
      clearTimeout(reconnectTimeout.value)
    }
  }

  const onMessageReceived = (event: MessageEvent<string>) => {
    const parsedData = parseArrivalPickData(event.data)

    if (parsedData && parsedData.picks && parsedData.pick_source_id) {
      handleArrivalData(parsedData)
    }
  }

  const onSocketOpen = () => {
    reconnectCount.value = 0
    resetTimeout()
  }

  const resetWebsocket = () => {
    if (!pickingWebSocket.value) return

    pickingWebSocket.value.removeEventListener('open', onSocketOpen)
    pickingWebSocket.value.removeEventListener('message', onMessageReceived)
    pickingWebSocket.value.close()
    pickingWebSocket.value = null

    resetTimeout()
  }

  const startReconnect = () => {
    reconnectTimeout.value = setTimeout(() => {
      reconnectCount.value += 1
      connectPickingWebSocket()
    }, 5_000)
  }

  const showTimedOutError = () => {
    console.error('Connection to websocket timed out\nwill retry automatically')
  }

  const connectPickingWebSocket = () => {
    pickingWebSocket.value = new WebSocket(`${SOCKET_BASE_URL}/wsarrivalpick`)

    pickingWebSocket.value.addEventListener('open', onSocketOpen)
    pickingWebSocket.value.addEventListener('message', onMessageReceived)

    timeout.value = setTimeout(() => {
      resetWebsocket()
      showTimedOutError()
      startReconnect()
    }, 20_000)
  }

  const closePickingWebSocket = () => {
    if (!pickingWebSocket.value) return

    pickingWebSocket.value.close()
    pickingWebSocket.value = null
  }

  onMounted(() => {
    connectPickingWebSocket()
  })

  onUnmounted(() => {
    closePickingWebSocket()

    if (reconnectTimeout.value) clearTimeout(reconnectTimeout.value)
    if (timeout.value) clearTimeout(timeout.value)
  })
}

export default useArrivalSocket
