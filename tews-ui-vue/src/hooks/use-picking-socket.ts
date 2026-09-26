import { SOCKET_BASE_URL } from '@src/constants/env'
import { WebsocketPickingResponse } from '@src/types/waveform'
import { onMounted, onUnmounted, ref } from 'vue'

function usePickingSocket(onPick?: (pick: WebsocketPickingResponse) => void) {
  const pickingWebSocket = ref<WebSocket | null>(null)
  const timeout = ref<number | null>(null)
  const reconnectTimeout = ref<number | null>(null)
  const reconnectCount = ref(0)

  const handlePickingData = ({ network, station, picks }: WebsocketPickingResponse) => {
    if (!window.socketData) {
      window.socketData = {}
    }

    if (!network || !station || !picks) {
      return
    }

    const fullStationName = `${network}.${station}`

    if (!window.socketData[fullStationName]) {
      window.socketData[fullStationName] = {
        picks: {},
        arrivals: {}
      }
    }

    for (const pick of picks) {
      window.socketData[fullStationName].picks[pick._id] = {
        _id: pick._id,
        timestamp: pick.timestamp
      }
    }
  }

  const parsePickData = (data: string) => {
    try {
      const parsedData = JSON.parse(data) as WebsocketPickingResponse
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
    const parsedData = parsePickData(event.data)

    if (parsedData && parsedData.picks) {
      handlePickingData(parsedData)
      onPick?.(parsedData)
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
    pickingWebSocket.value = new WebSocket(`${SOCKET_BASE_URL}/wspicking`)
    // pickingWebSocket.value = new WebSocket(`http://localhost:3535/wspicking`)

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

export default usePickingSocket
