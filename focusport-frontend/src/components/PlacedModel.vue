<script setup>
import CityModelInstance from './CityModelInstance.vue'

const props = defineProps({
  item: { type: Object, required: true },
  isSelected: { type: Boolean, default: false },
  slotFootprint: { type: Number, default: 0 }
})

const emit = defineEmits(['select'])
const DEFAULT_CITY_Y = 1.7
const SAFE_CITY_Y = 1.7

const getSafeY = (value) => Math.max(Number(value ?? DEFAULT_CITY_Y), SAFE_CITY_Y) + 0.01
</script>

<template>
  <TresGroup
    :position="[item.position_x ?? 0, getSafeY(item.position_y), item.position_z ?? 0]"
    :rotation="[0, ((item.rotation_y ?? 0) * Math.PI) / 180, 0]"
    :scale="item.scale ?? 1"
    @click="emit('select')"
  >
    <CityModelInstance
      :item="item"
      :is-selected="isSelected"
      :show-selection-indicator="true"
      :target-footprint="slotFootprint > 0 ? slotFootprint * 0.82 : 0"
    />
  </TresGroup>
</template>
