<script setup lang="ts">
import { getDepthColor, getMagnitudeWidth } from '@src/utils/event'

const magnitudes = [...new Array(8)].map((_, index) => index + 1)
</script>

<template>
  <div class="bg-white/50 backdrop-blur-lg rounded-md shadow-sm text-xs text-black max-md:hidden">
    <div class="text-xs font-semibold p-1 border-b border-slate-400/50">Depth in km</div>
    <div class="grid grid-cols-5 border-b border-slate-400/50">
      <div class="py-1 px-2 flex items-center gap-2">
        <div class="mask mask-square w-3 bg-[#f00]">&nbsp;</div>
        <div>&lt; 50</div>
      </div>

      <div v-for="depth in [50, 100, 250, 600]" :key="depth" class="py-1 px-2 flex items-center gap-2">
        <div class="mask mask-square w-3" :style="{ backgroundColor: getDepthColor(depth) }">&nbsp;</div>
        <div>{{ depth }}</div>
      </div>
    </div>
    <div class="text-xs font-semibold p-1 border-b border-slate-400/50">Magnitudes</div>
    <div class="flex items-center justify-center">
      <div v-for="magnitude in magnitudes" :key="magnitude" class="py-2 px-1 flex items-center gap-1">
        <div
          class="mask mask-circle w-3 bg-primary border-2 rounded-full border-black"
          :style="{
            width: `${getMagnitudeWidth(magnitude)}px`,
            height: `${getMagnitudeWidth(magnitude)}px`
          }">
          &nbsp;
        </div>
        <div>{{ magnitude }}</div>
      </div>
    </div>
  </div>
</template>
