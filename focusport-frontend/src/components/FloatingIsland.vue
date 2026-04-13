<script setup>
import { computed, ref } from 'vue'
import { useLoop } from '@tresjs/core'

const props = defineProps({
  scale: { type: Number, default: 1.0 },
  theme: { type: String, default: 'city' }
})

const islandFloatOffset = ref({ y: 0 })
const CITY_SURFACE_Y = 1.7
const ROAD_Y = 1.69
const LANE_Y = 1.705

useLoop().onBeforeRender(({ elapsed }) => {
  if (props.theme === 'city') {
    islandFloatOffset.value.y = 0
    return
  }
  islandFloatOffset.value.y = Math.sin(elapsed * 0.3) * 0.12
})

const themeColors = computed(() => ({
  main: { grass: '#69b04e', ground: '#5a8a4b', rock: '#6b5f54', glow: '#8be0ff' },
  house: { grass: '#b99b68', ground: '#8d6f49', rock: '#6d5842', glow: '#ffd69e' },
  city: {
    pad: '#23324d',
    padAccent: '#2b4b7c',
    road: '#1c273b',
    lane: '#73e0ff',
    glow: '#6d5cff',
    skyline: '#7db1ff',
    greenery: '#4ae8a8'
  }
}[props.theme] || {
  grass: '#69b04e',
  ground: '#5a8a4b',
  rock: '#6b5f54',
  glow: '#8be0ff'
}))

const roadLines = [-14, -7, 0, 7, 14]
const skylineBlocks = [
  [-19.5, 3.8, -17.5, 2.2, 3.8, 2.2],
  [-16.5, 5.1, -16.0, 1.6, 5.8, 1.6],
  [19.5, 4.8, -17.5, 2.3, 5.4, 2.3],
  [16.5, 3.6, -16.0, 1.6, 3.8, 1.6],
  [-19.5, 4.3, 17.5, 2.2, 4.6, 2.2],
  [-16.5, 3.1, 16.0, 1.6, 3.0, 1.6],
  [19.5, 5.3, 17.5, 2.3, 6.1, 2.3],
  [16.5, 3.9, 16.0, 1.6, 4.0, 1.6]
]

const islandPosition = computed(() => [0, islandFloatOffset.value.y, 0])
</script>

<template>
  <TresGroup :position="islandPosition" :scale="scale">
    <template v-if="theme === 'city'">
      <TresMesh :position="[0, CITY_SURFACE_Y - 0.08, 0]" :rotation="[-Math.PI / 2, 0, 0]" receive-shadow>
        <TresPlaneGeometry :args="[43.6, 43.6]" />
        <TresMeshStandardMaterial :color="themeColors.padAccent" :emissive="themeColors.glow" :emissive-intensity="0.08" />
      </TresMesh>

      <TresMesh :position="[0, CITY_SURFACE_Y, 0]" :rotation="[-Math.PI / 2, 0, 0]" receive-shadow>
        <TresPlaneGeometry :args="[42, 42]" />
        <TresMeshStandardMaterial :color="themeColors.pad" :emissive="themeColors.glow" :emissive-intensity="0.05" />
      </TresMesh>

      <TresMesh :position="[0, CITY_SURFACE_Y + 0.02, 0]" :rotation="[-Math.PI / 2, 0, 0]">
        <TresRingGeometry :args="[11.6, 15.2, 48]" />
        <TresMeshStandardMaterial :color="themeColors.glow" :emissive="themeColors.glow" :emissive-intensity="0.5" :transparent="true" :opacity="0.22" />
      </TresMesh>

      <TresMesh :position="[0, CITY_SURFACE_Y + 0.03, 0]" :rotation="[-Math.PI / 2, 0, Math.PI / 4]">
        <TresPlaneGeometry :args="[32, 32, 14, 14]" />
        <TresMeshStandardMaterial :color="themeColors.glow" :emissive="themeColors.glow" :emissive-intensity="0.35" :transparent="true" :opacity="0.06" wireframe />
      </TresMesh>

      <TresMesh
        v-for="x in roadLines"
        :key="`road-x-${x}`"
        :position="[x, ROAD_Y, 0]"
        :rotation="[-Math.PI / 2, 0, 0]"
      >
        <TresPlaneGeometry :args="[1.7, 42]" />
        <TresMeshStandardMaterial :color="themeColors.road" />
      </TresMesh>

      <TresMesh
        v-for="z in roadLines"
        :key="`road-z-${z}`"
        :position="[0, ROAD_Y, z]"
        :rotation="[-Math.PI / 2, 0, 0]"
      >
        <TresPlaneGeometry :args="[42, 1.7]" />
        <TresMeshStandardMaterial :color="themeColors.road" />
      </TresMesh>

      <TresMesh
        v-for="x in roadLines"
        :key="`lane-x-${x}`"
        :position="[x, LANE_Y, 0]"
        :rotation="[-Math.PI / 2, 0, 0]"
      >
        <TresPlaneGeometry :args="[0.14, 39.2]" />
        <TresMeshStandardMaterial :color="themeColors.lane" :emissive="themeColors.lane" :emissive-intensity="0.6" />
      </TresMesh>

      <TresMesh
        v-for="z in roadLines"
        :key="`lane-z-${z}`"
        :position="[0, LANE_Y, z]"
        :rotation="[-Math.PI / 2, 0, 0]"
      >
        <TresPlaneGeometry :args="[39.2, 0.14]" />
        <TresMeshStandardMaterial :color="themeColors.lane" :emissive="themeColors.lane" :emissive-intensity="0.6" />
      </TresMesh>

      <TresGroup v-for="(block, index) in skylineBlocks" :key="`skyline-${index}`" :position="[block[0], CITY_SURFACE_Y + block[1] / 2, block[2]]">
        <TresMesh>
          <TresBoxGeometry :args="[block[3], block[1], block[5]]" />
          <TresMeshStandardMaterial :color="themeColors.skyline" :emissive="themeColors.glow" :emissive-intensity="0.18" :transparent="true" :opacity="0.22" />
        </TresMesh>
      </TresGroup>

      <TresGroup v-for="corner in [[-18, -18], [18, -18], [-18, 18], [18, 18]]" :key="`greenery-${corner[0]}-${corner[1]}`" :position="[corner[0], CITY_SURFACE_Y, corner[1]]">
        <TresMesh :position="[0, 0.28, 0]">
          <TresCylinderGeometry :args="[0.32, 0.32, 0.55, 10]" />
          <TresMeshStandardMaterial color="#113450" />
        </TresMesh>
        <TresMesh :position="[0, 0.72, 0]">
          <TresSphereGeometry :args="[0.45, 10, 10]" />
          <TresMeshStandardMaterial :color="themeColors.greenery" :emissive="themeColors.greenery" :emissive-intensity="0.18" />
        </TresMesh>
      </TresGroup>
    </template>

    <template v-else>
      <TresMesh :position="[0, 0, 0]" receive-shadow>
        <TresCylinderGeometry :args="[18, 22, 3, 24]" />
        <TresMeshStandardMaterial :color="themeColors.ground" :flatShading="true" />
      </TresMesh>

      <TresMesh :position="[0, 1.55, 0]" receive-shadow>
        <TresCylinderGeometry :args="[17.5, 17.5, 0.15, 24]" />
        <TresMeshStandardMaterial :color="themeColors.grass" />
      </TresMesh>

      <TresMesh :position="[0, -4, 0]">
        <TresConeGeometry :args="[20, 5, 16]" />
        <TresMeshStandardMaterial :color="themeColors.rock" :flatShading="true" />
      </TresMesh>
    </template>
  </TresGroup>
</template>
