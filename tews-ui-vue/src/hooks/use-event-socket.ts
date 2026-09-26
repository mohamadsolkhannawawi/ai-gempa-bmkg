import { SOCKET_BASE_URL } from '@src/constants/env'
import { WSEvent } from '@src/types/ws-event'
import { onMounted, onUnmounted, ref } from 'vue'

function useEventSocket(messageHandler: (data: WSEvent) => void) {
  const isConnecting = ref(true)
  const wsEvent = ref<WebSocket | null>(null)
  const timeout = ref<number | null>(null)
  const reconnectTimeout = ref<number | null>(null)
  const reconnectCount = ref(0)

  const startReconnect = () => {
    reconnectTimeout.value = setTimeout(() => {
      reconnectCount.value += 1
      connectWebsocket()
    }, 5_000)
  }

  const showTimedOutError = () => {
    console.error('Connection to websocket timed out\nwill retry automatically')
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

  const onSocketOpen = () => {
    reconnectCount.value = 0
    isConnecting.value = false

    resetTimeout()
  }

  const onMessageReceived = (event: MessageEvent<string>) => {
    try {
      if (!event.data) throw Error('empty response from wsevent')
      const parsed = JSON.parse(event.data) as WSEvent
      if (typeof parsed.longitude === 'number' && typeof parsed.latitude === 'number') {
        messageHandler(parsed)
      }
    } catch (error) {
      console.error(error)
    }
  }

  const resetWebsocket = () => {
    isConnecting.value = false

    if (!wsEvent.value) return

    wsEvent.value.removeEventListener('open', onSocketOpen)
    wsEvent.value.removeEventListener('message', onMessageReceived)
    wsEvent.value.close()
    wsEvent.value = null

    resetTimeout()
  }

  const connectWebsocket = () => {
    const ws = new WebSocket(`${SOCKET_BASE_URL}/wsevent`)
    // const ws = new WebSocket(`http://localhost:3535/wsevent`)

    isConnecting.value = true

    ws.addEventListener('open', onSocketOpen)
    ws.addEventListener('message', onMessageReceived)

    wsEvent.value = ws

    timeout.value = setTimeout(() => {
      resetWebsocket()
      showTimedOutError()
      startReconnect()
    }, 20_000)
  }

  onMounted(() => {
    connectWebsocket()
  })

  onUnmounted(() => {
    resetWebsocket()

    if (reconnectTimeout.value) clearTimeout(reconnectTimeout.value)
    if (timeout.value) clearTimeout(timeout.value)
  })

  return {
    isConnecting
  }
}

export default useEventSocket
