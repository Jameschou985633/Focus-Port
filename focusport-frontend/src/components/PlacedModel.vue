<script setup>
import { computed } from 'vue'
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

const position = computed(() => ({
  x: Number(props.item?.position_x ?? props.item?.position?.x ?? 0),
  y: Number(props.item?.position_y ?? props.item?.position?.y ?? DEFAULT_CITY_Y),
  z: Number(props.item?.position_z ?? props.item?.position?.z ?? 0)
}))

const rotationY = computed(() => Number(props.item?.rotation_y ?? props.item?.rotation?.y ?? 0))

const displayItem = computed(() => ({
  ...props.item,
  model_path: props.item?.model_path || props.item?.modelPath || '',
  item_code: props.item?.item_code || props.item?.itemCode || '',
  placement_type: props.item?.placement_type || props.item?.placementType || '',
  category: props.item?.category || props.item?.raw?.category || ''
}))

const safeScale = computed(() => {
  const raw = Number(props.item?.scale)
  if (!Number.isFinite(raw)) return 1
  // Old placed records may contain 0/negative scale and make model invisible.
  return Math.max(0.2, raw)
})
</script>

<template>
  <TresGroup
    :position="[position.x, getSafeY(position.y), position.z]"
    :rotation="[0, (rotationY * Math.PI) / 180, 0]"
    :scale="safeScale"
    @click="emit('select')"
  >
    <CityModelInstance
      :item="displayItem"
      :is-selected="isSelected"
      :show-selection-indicator="true"
      :target-footprint="slotFootprint > 0 ? slotFootprint * 0.82 : 0"
    />
  </TresGroup>
</template>
