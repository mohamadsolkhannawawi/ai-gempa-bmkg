<script setup lang="ts">
import { getRecordStreamAPI, RecordStreamResponse } from '@src/api-service/record-stream'
import { TimestampAxis } from '@src/domain/trace-view/timestamp-axis'
import { Arrival } from '@src/types/arrival'
import { Station } from '@src/types/station'
import { PhaseType } from '@src/types/waveform'
import { downsampleWaveform } from '@src/utils/waveform'
import * as d3 from 'd3'
import { addSeconds } from 'date-fns'
import { isEqual } from 'lodash'
import { ref, watch } from 'vue'

const WAVEFORM_HEIGHT = 140

type ChannelWaveforms = Record<
  string,
  | (RecordStreamResponse & {
      min: number
      max: number
      times: number[]
    })
  | null
>
type XScale = d3.ScaleTime<number, number, never>

const props = defineProps<{
  station: Station
  arrivals: {
    p?: Arrival
    s?: Arrival
  }
  updatedArrivals: {
    p?: Arrival
    s?: Arrival
  }
  width: number
  startTime: Date
  endTime: Date
  originTime: Date
  xScale: XScale
}>()

const emits = defineEmits<{
  (e: 'change-phase', timeStamp: Date): void
}>()

const { xScale, width } = props

const canvas = ref<HTMLCanvasElement | null>(null)
const canvasPicker = ref<HTMLCanvasElement | null>(null)
const canvasContextRef = ref<CanvasRenderingContext2D | null>(null)
const canvasPickerContextRef = ref<CanvasRenderingContext2D | null>(null)
const channelWaveforms = ref<ChannelWaveforms>({})
const updatedXScale = ref(xScale)

const drawPick = (
  canvasContext: CanvasRenderingContext2D,
  newXScale: XScale,
  position: Date,
  phaseType: PhaseType | 'OT',
  isUpdated = false,
  canvasHeight: number
) => {
  const x = newXScale(position)

  const getColor = () => {
    if (phaseType === 'OT') {
      return 'yellow'
    }
    if (isUpdated) {
      return phaseType === 'P' ? '#DF2C2C' : '#38BDF8'
    }
    return phaseType === 'P' ? 'rgb(167, 21, 26, 0.9)' : 'rgb(56, 189, 248, 0.6)'
  }

  const color = getColor()

  canvasContext.beginPath()
  canvasContext.moveTo(x, 0)
  canvasContext.lineWidth = 2
  canvasContext.lineTo(x, canvasHeight)
  canvasContext.strokeStyle = color
  canvasContext.stroke()

  canvasContext.beginPath()
  canvasContext.font = 'bold 13px Arial'
  canvasContext.fillStyle = color

  if (phaseType !== 'OT') {
    if (isUpdated) {
      canvasContext.fillText(`${phaseType}new`, x + 2, 14)
    } else {
      canvasContext.fillText(phaseType, x + 2, 14)
    }
  }
}

const drawWaveform = (
  canvasContext: CanvasRenderingContext2D,
  channelWaveform: RecordStreamResponse & {
    min: number
    max: number
    times: number[]
  },
  yStart: number,
  newXScale: XScale
) => {
  const filledWaveform = channelWaveform.waveform as number[]
  const min = channelWaveform.min!
  const max = channelWaveform.max!

  const yScale = d3.scaleLinear().domain([min, max]).range([WAVEFORM_HEIGHT, 0])

  let firstIndex = true

  canvasContext.clearRect(0, yStart, width, WAVEFORM_HEIGHT)

  const chunkSize = 100

  for (let i = 0; i < filledWaveform.length; i += chunkSize) {
    const chunk = filledWaveform.slice(i, i + chunkSize)

    chunk.forEach((waveform, chunkIndex) => {
      const index = i + chunkIndex // Calculate the actual index
      const time = channelWaveform.times[index]

      const x = newXScale(time)
      const y = yScale(waveform)

      if (firstIndex) {
        canvasContext.moveTo(x, y + yStart)
        firstIndex = false
      } else {
        canvasContext.lineTo(x, y + yStart)
      }
    })
  }

  // filledWaveform.forEach((waveform, index) => {
  //   const time = channelWaveform.times[index]

  //   const x = newXScale(time)
  //   const y = yScale(waveform)

  //   if (firstIndex) {
  //     canvasContext.moveTo(x, y + yStart)
  //     firstIndex = false
  //   } else {
  //     canvasContext.lineTo(x, y + yStart)
  //   }
  // })

  canvasContext.strokeStyle = '#75ecb8'
  canvasContext.stroke()
}

const drawChartDivider = (
  canvasContext: CanvasRenderingContext2D,
  newChannelWaveforms: ChannelWaveforms,
  newStation: Station,
  newXScale: XScale
) => {
  newStation.channel.forEach((channel, index) => {
    const y = index * WAVEFORM_HEIGHT

    const waveformData = newChannelWaveforms[channel]
    if (waveformData) {
      drawWaveform(canvasContext, waveformData, y, newXScale)
    }

    canvasContext.beginPath()
    canvasContext.moveTo(0, y)
    canvasContext.lineWidth = 1
    canvasContext.lineTo(width, y)
    canvasContext.strokeStyle = 'rgba(255, 255, 255, 0.3)'
    canvasContext.stroke()

    canvasContext.fillStyle = 'white'
    canvasContext.font = '11px Arial'
    canvasContext.fillText(channel, 5, y + WAVEFORM_HEIGHT / 2 + 10)
  })
}

const drawPickers = (
  canvasContext: CanvasRenderingContext2D,
  newArrivals: Arrival[],
  newUpdatedArrivals: Arrival[],
  canvasHeight: number,
  newXScale: XScale
) => {
  newArrivals.forEach((arrival) => {
    drawPick(
      canvasContext,
      newXScale,
      new Date(arrival.timestamp),
      arrival.phase_type as PhaseType,
      false,
      canvasHeight
    )
  })

  newUpdatedArrivals.forEach((arrival) => {
    drawPick(canvasContext, newXScale, new Date(arrival.timestamp), arrival.phase_type as PhaseType, true, canvasHeight)
  })

  drawPick(canvasContext, newXScale, new Date(props.originTime), 'OT', true, canvasHeight)
}

const clearCanvas = (canvasContext: CanvasRenderingContext2D, canvasHeight: number) => {
  canvasContext.clearRect(0, 0, width, canvasHeight)
}

const drawMousePointer = (
  canvasContext: CanvasRenderingContext2D,
  newXScale: XScale,
  position: Date,
  newArrivals: Arrival[],
  newUpdatedArrivals: Arrival[],
  canvasHeight: number
) => {
  clearCanvas(canvasContext, canvasHeight)
  drawPickers(canvasContext, newArrivals, newUpdatedArrivals, canvasHeight, newXScale)

  const x = newXScale(position)

  // create line
  canvasContext.beginPath()
  canvasContext.moveTo(x, 0)
  canvasContext.lineTo(x, canvasHeight)
  canvasContext.strokeStyle = 'green'
  canvasContext.stroke()

  // draw text
  // canvasContext.beginPath()
  // canvasContext.font = '13px Arial'
  // canvasContext.fillStyle = 'yellow'
  // canvasContext.fillText('P', x + 2, 14)

  canvasContext.beginPath()
  // canvasContext.fillRect(x + 1, canvasHeight - 18, 150, 20)
  canvasContext.fillStyle = 'white'
  canvasContext.font = '11px Arial'
  canvasContext.fillText(position.toISOString(), x + 2, 10)
}

const drawChartPicker = (
  newCanvas: HTMLCanvasElement,
  newArrivals: Arrival[],
  newUpdatedArrivals: Arrival[],
  newStation: Station,
  newXScaleProps: XScale
) => {
  const canvasHeight = newStation.channel.length * WAVEFORM_HEIGHT
  const d3Canvas = d3.select(newCanvas).attr('width', width).attr('height', canvasHeight)

  let canvasContext = canvasPickerContextRef.value

  if (!canvasContext) {
    canvasContext = d3Canvas.node()!.getContext('2d')!
    canvasPickerContextRef.value = canvasContext
  }

  const addMouseEventHandler = (newXScale: XScale) => {
    d3Canvas.on('mousemove', function (event) {
      const mousePosition = d3.pointer(event)
      const scale = newXScale
      const data = scale.invert(mousePosition[0])

      drawMousePointer(canvasContext, scale, data, newArrivals, newUpdatedArrivals, canvasHeight)
    })

    d3Canvas.on('mouseleave', function () {
      clearCanvas(canvasContext, canvasHeight)
      drawPickers(canvasContext, newArrivals, newUpdatedArrivals, canvasHeight, newXScale)
    })

    d3Canvas.on('dblclick', function (event) {
      const position = d3.pointer(event)
      const scale = newXScale
      const data = scale.invert(position[0])

      emits('change-phase', data)
    })
  }

  const zoomed = (event: any) => {
    const newXScale = event.transform.rescaleX(xScale)
    updatedXScale.value = newXScale

    clearCanvas(canvasContext, canvasHeight)
    drawPickers(canvasContext, newArrivals, newUpdatedArrivals, canvasHeight, newXScale)
    addMouseEventHandler(newXScale)

    if (canvasContextRef.value) {
      clearCanvas(canvasContextRef.value, canvasHeight)
      drawChartDivider(canvasContextRef.value, channelWaveforms.value, props.station, newXScale)
    }
  }
  const zoom = d3
    .zoom()
    .scaleExtent([1, 80])
    .extent([
      [0, 0],
      [width - 0, canvasHeight]
    ])
    .translateExtent([
      [0, -Infinity],
      [width - 0, Infinity]
    ])
    .on('zoom', zoomed)

  // @ts-expect-error
  d3Canvas.call(zoom)

  // disable zoom double click
  d3Canvas.on('dblclick.zoom', null)

  clearCanvas(canvasContext, canvasHeight)
  drawPickers(canvasContext, newArrivals, newUpdatedArrivals, canvasHeight, newXScaleProps)
  addMouseEventHandler(newXScaleProps)
}

const drawChart = (
  newCanvas: HTMLCanvasElement,
  newChannelWaveforms: ChannelWaveforms,
  newStation: Station,
  newXScale: XScale
) => {
  const canvasHeight = newStation.channel.length * WAVEFORM_HEIGHT
  const d3Canvas = d3.select(newCanvas).attr('width', width).attr('height', canvasHeight)

  let canvasContext = canvasContextRef.value

  if (!canvasContext) {
    canvasContext = d3Canvas.node()!.getContext('2d')!
    canvasContextRef.value = canvasContext
  }

  clearCanvas(canvasContext, canvasHeight)
  drawChartDivider(canvasContext, newChannelWaveforms, newStation, newXScale)
}

const fetchAllWaveforms = async (newStation: Station) => {
  const result = await Promise.all(
    newStation.channel.map(async (channel) => {
      const response = await getRecordStreamAPI({
        network: newStation.network,
        station: newStation.code,
        channel,
        location: newStation.location,
        originTime: props.originTime,
        startTime: props.startTime,
        endTime: props.endTime
      })

      return {
        recordStream: typeof response === 'object' ? response : null,
        channel
      }
    })
  )

  const newChannelWaveforms: typeof channelWaveforms.value = {}

  result.forEach((r) => {
    const recordStream = r.recordStream

    if (recordStream) {
      const filledWaveform = recordStream.waveform.map((waveform, index) => {
        if (waveform === null) {
          return recordStream.waveform[index - 1] ?? 0
        }
        return waveform
      })

      const { downsampledData, downsampleFactor } = downsampleWaveform(filledWaveform, recordStream.sampling_rate, 20)

      const times = downsampledData.map((waveform, index) =>
        addSeconds(props.startTime, downsampleFactor * recordStream.delta * index).getTime()
      )

      const min = Math.min(...downsampledData)
      const max = Math.max(...downsampledData)

      newChannelWaveforms[r.channel] = {
        ...recordStream,
        waveform: downsampledData,
        min,
        max,
        times
      }
    }
  })

  channelWaveforms.value = newChannelWaveforms
}

watch(
  () => props.station,
  (newStation, oldStation) => {
    if (isEqual(newStation, oldStation)) return
    fetchAllWaveforms(newStation)
  },
  { immediate: true }
)

watch(
  [canvasPicker, () => props.arrivals, () => props.updatedArrivals, () => props.station],
  ([newCanvasPicker, newArrivals, newUpdatedArrivals, newStation]) => {
    if (!newCanvasPicker) return

    const chartArrivals: Arrival[] = []
    if (newArrivals.p) chartArrivals.push(newArrivals.p)
    if (newArrivals.s) chartArrivals.push(newArrivals.s)

    const updatedChartArrivals: Arrival[] = []
    if (newUpdatedArrivals.p) updatedChartArrivals.push(newUpdatedArrivals.p)
    if (newUpdatedArrivals.s) updatedChartArrivals.push(newUpdatedArrivals.s)

    drawChartPicker(newCanvasPicker, chartArrivals, updatedChartArrivals, newStation, updatedXScale.value)
  },
  { deep: true }
)

watch([canvas, channelWaveforms], ([newCanvas, newChannelWaveforms]) => {
  if (!newCanvas) return
  drawChart(newCanvas, newChannelWaveforms, props.station, updatedXScale.value)
})
</script>

<template>
  <div class="h-[420px] overflow-y-scroll relative">
    <canvas ref="canvas" class="w-full cursor-pointer" />
    <canvas ref="canvasPicker" class="w-full absolute top-0 left-0" />
  </div>
  <TimestampAxis
    :updated-x-scale="updatedXScale"
    :width="width"
    :start-time="startTime.getTime()"
    :end-time="endTime.getTime()" />
</template>
