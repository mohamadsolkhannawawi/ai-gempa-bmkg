<template>
  <div ref="timeRef">
    <svg>
      <g />
    </svg>
  </div>
</template>

<script setup lang="ts">
import * as d3 from 'd3'
import { onMounted, ref, watch } from 'vue'

type XScale = d3.ScaleTime<number, number, never>

const props = defineProps<{
  timeFormat?: string
  startTime: number
  endTime: number
  width: number
  updatedXScale?: XScale
}>()

const timeRef = ref<HTMLDivElement | null>(null)
const xAxisSvgRef = ref()
const gx = ref<d3.Selection<SVGGElement, unknown, HTMLElement, any>>()

const TIMESTAMP_WIDTH = props.width // TODO: get width from parent

const createXAxis = (newWidth: number) => {
  if (!timeRef.value) return

  xAxisSvgRef.value = d3
    .select(timeRef.value)
    .select('svg')
    .attr('width', newWidth)
    .attr('height', 40) // TODO: get height from parent
    .select('g')
}

onMounted(() => {
  if (!timeRef.value) return

  createXAxis(TIMESTAMP_WIDTH)
})

const renderXAxisWithScale = (g: any, newXScale: XScale) => {
  return g.call(
    // @ts-expect-error
    d3.axisBottom(newXScale).tickFormat(d3.timeFormat(props.timeFormat ?? '%H:%M:%S'))
  )
}

const drawTimestamp = (
  newStartTime: number,
  newEndTime: number,
  newWidth: number,
  newXAxisSvgRef: any,
  newXScale?: XScale
) => {
  const xScale = newXScale ?? d3.scaleLinear().domain([newStartTime, newEndTime]).range([0, newWidth])

  gx.value = newXAxisSvgRef.attr('class', 'axis axis--x').attr('color', '#ffffff').call(renderXAxisWithScale, xScale)
}

watch(
  [() => props.startTime, () => props.endTime, () => props.width, xAxisSvgRef],
  ([newStartTime, newEndTime, newWidth, newXAxisSvgRef]) => {
    if (newXAxisSvgRef) {
      drawTimestamp(newStartTime, newEndTime, newWidth, newXAxisSvgRef)
    }
  },
  { immediate: true }
)

watch(
  () => props.updatedXScale,
  (newXScale) => {
    if (newXScale && gx.value) {
      gx.value.call(renderXAxisWithScale, newXScale)
    }
  }
)

watch(
  () => props.width,
  (newWidth) => {
    createXAxis(newWidth)
  }
)
</script>
