<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import axios from 'axios'
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'

import CityModelInstance from './CityModelInstance.vue'
import FloatingIsland from './FloatingIsland.vue'
import PlacedModel from './PlacedModel.vue'
import { unifiedShopApi } from '../api'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'
import '../assets/kenney-ui/kenney-hud.css'

const props = defineProps({
  previewMode: {
    type: Boolean,
    default: false
  }
})

const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const currentUsername = ref(localStorage.getItem('username') || 'guest')

const citySlots = ref([])
const placedDecorations = ref([])
const selectedDecoration = ref(null)
const placementItem = ref(null)
const isPlacementMode = ref(false)
const isPlacementSubmitting = ref(false)
const hoveredPlacementSlotId = ref('')
const supportsHover = ref(false)


const userGrowth = ref({
  exp: 0,
  level: 1,
  streak_days: 0,
  discipline_score: 50,
  focus_energy: 0,
  total_focus_minutes: 0
})


const CITY_THEME = {
  sky: '#050914',
  ambient: '#80d2ff',
  ambientIntensity: 1.15,
  directional: '#78b4ff',
  directionalIntensity: 1.55,
  fogPlane: '#0b1022',
  horizonGlow: '#6d5cff'
}

const SAFE_CITY_Y = 1.7

const focusMinutes = computed(() => userGrowth.value.total_focus_minutes || 0)

const normalizePlacementType = (value = '', category = '') => {
  const placement = String(value || '').trim().toLowerCase()
  if ([
    'building',
    'buildings',
    'structure',
    'structures',
    'vehicle',
    'vehicles',
    'path',
    'paths',
    'road',
    'roads',
    'platform',
    'ground',
    'fixed_scene',
    'fixed-scene'
  ].includes(placement)) {
    return 'building'
  }
  if (['greenery', 'green', 'plant', 'plants', 'tree', 'trees', 'flora'].includes(placement)) {
    return 'greenery'
  }

  const categoryValue = String(category || '').trim().toLowerCase()
  if (['structures', 'vehicles', 'paths', 'roads'].includes(categoryValue)) {
    return 'building'
  }
  if (['plants', 'trees', 'greenery'].includes(categoryValue)) {
    return 'greenery'
  }

  return ''
}

const placementType = computed(() => {
  const item = placementItem.value
  if (!item) return ''
  return normalizePlacementType(
    item.placementType || item.placement_type || '',
    item.category || item.raw?.category || ''
  )
})

const occupiedSlotIds = computed(() => {
  const occupied = new Set()
  placedDecorations.value.forEach((item) => {
    if (item.slot_id) occupied.add(item.slot_id)
  })
  return occupied
})

const compatibleSlots = computed(() => {
  const type = placementType.value
  if (!type) return []
  return citySlots.value.filter((slot) => (
    slot.enabled !== false &&
    normalizePlacementType(slot.slot_type) === type &&
    !occupiedSlotIds.value.has(slot.slot_id)
  ))
})

const slotFootprintById = computed(() => (
  Object.fromEntries(citySlots.value.map((slot) => [slot.slot_id, Number(slot.footprint || 0)]))
))

const previewSlot = computed(() => {
  if (!isPlacementMode.value) return null
  return compatibleSlots.value.find((slot) => slot.slot_id === hoveredPlacementSlotId.value) || compatibleSlots.value[0] || null
})

const previewTargetFootprint = computed(() => {
  if (!previewSlot.value) return 0
  return previewSlot.value.slot_type === 'building'
    ? Number(previewSlot.value.footprint || 2.2) * 0.82
    : Number(previewSlot.value.footprint || 1.8)
})

const loadCitySlots = async () => {
  const normalizeSlots = (slots = []) => slots.map((slot) => ({
    ...slot,
    slot_type: normalizePlacementType(slot.slot_type || slot.type || '', slot.category || '')
  })).filter((slot) => Boolean(slot.slot_type))

  try {
    const response = await axios.get(`${API_BASE}/static/city_layout_slots.json`)
    const slots = normalizeSlots(response.data?.slots || [])
    citySlots.value = slots
    if (slots.length) return
  } catch (error) {
    console.error('Failed to load city slots', error)
  }

  try {
    const fallback = await fetch('/city_layout_slots.json')
    const payload = await fallback.json()
    citySlots.value = normalizeSlots(payload?.slots || [])
  } catch (error) {
    console.error('Failed to load fallback city slots', error)
    citySlots.value = []
  }
}

const upsertPlacedDecoration = (item) => {
  if (!item?.id) return
  const next = placedDecorations.value.filter((entry) => entry.id !== item.id)
  next.push(item)
  next.sort((left, right) => (left.id || 0) - (right.id || 0))
  placedDecorations.value = next
}

const loadPlacedDecorations = async ({ preserveExisting = false, fallbackItem = null, showRefreshError = false } = {}) => {
  try {
    const response = await unifiedShopApi.placed(currentUsername.value, { dimension: '3D' })
    placedDecorations.value = response.data.items || []
    inventoryStore.replacePlacedItemsForDimension('PHYSICAL', response.data.items || [])
    return true
  } catch (error) {
    console.error('Failed to load placed physical assets', error)
    if (!preserveExisting) {
      placedDecorations.value = []
    }
    if (fallbackItem) {
      upsertPlacedDecoration(fallbackItem)
    }
    if (showRefreshError) {
      window.alert(error.response?.data?.detail || 'Placement succeeded, but refresh failed. Please reload and verify.')
    }
    return false
  }
}

const loadUserGrowth = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/growth/${currentUsername.value}`)
    userGrowth.value = {
      ...userGrowth.value,
      ...(response.data?.growth || response.data || {})
    }
  } catch (error) {
    console.error('Failed to load growth data', error)
  }
}

const setPreviewSlot = (slot) => {
  if (!slot?.slot_id) return
  hoveredPlacementSlotId.value = slot.slot_id
}

const getSafeCityY = (value) => Math.max(Number(value ?? SAFE_CITY_Y), SAFE_CITY_Y) + 0.01

const resetPreviewSlot = () => {
  hoveredPlacementSlotId.value = compatibleSlots.value[0]?.slot_id || ''
}

const getSlotMarkerRadius = (slot) => Number(slot?.footprint || (slot?.slot_type === 'building' ? 2.2 : 1.8)) * 0.86

const getSlotRingArgs = (slot) => {
  const footprint = Number(slot?.footprint || (slot?.slot_type === 'building' ? 2.2 : 1.8))
  if (slot?.slot_type === 'building') {
    return [footprint * 0.35, footprint * 0.63, 6]
  }
  return [footprint * 0.31, footprint * 0.57, 24]
}

const handleSlotPointerEnter = (slot) => {
  if (!isPlacementMode.value) return
  setPreviewSlot(slot)
}

const syncPlacementModeFromStore = () => {
  if (props.previewMode) return
  const draft = inventoryStore.placementDraft
  if (dimensionStore.activeDimension !== 'PHYSICAL' || !draft || draft.dimension !== 'PHYSICAL') {
    if (!isPlacementSubmitting.value) {
      isPlacementMode.value = false
      placementItem.value = null
      hoveredPlacementSlotId.value = ''
    }
    return
  }

  placementItem.value = draft
  selectedDecoration.value = null
  isPlacementMode.value = true

  if (!citySlots.value.length) {
    return
  }

  if (!['building', 'greenery'].includes(placementType.value)) {
    window.alert('当前资产类型暂不支持 3D 城市放置。')
    inventoryStore.cancelPlacement()
    return
  }

  if (!compatibleSlots.value.length) {
    const message = placementType.value === 'greenery' ? '当前没有可用的绿化槽位。' : '当前没有可用的建筑槽位。'
    window.alert(message)
    inventoryStore.cancelPlacement()
    return
  }

  if (!compatibleSlots.value.some((slot) => slot.slot_id === hoveredPlacementSlotId.value)) {
    resetPreviewSlot()
  }
}

const handleSlotClick = async (slot) => {
  if (!slot) return
  if (!supportsHover.value && previewSlot.value?.slot_id !== slot.slot_id) {
    setPreviewSlot(slot)
    return
  }
  await confirmPlacement(slot)
}

const exitPlacementMode = () => {
  if (isPlacementSubmitting.value) return
  isPlacementMode.value = false
  placementItem.value = null
  hoveredPlacementSlotId.value = ''
  inventoryStore.cancelPlacement()
}

const confirmPlacement = async (slot) => {
  if (isPlacementSubmitting.value || !placementItem.value || !slot?.slot_id) return
  isPlacementSubmitting.value = true
  try {
    const response = await unifiedShopApi.place(
      currentUsername.value,
      placementItem.value.itemId || placementItem.value.item_id || placementItem.value.id,
      slot.slot_id,
      slot.x || 0,
      getSafeCityY(slot.y),
      slot.z || 0,
      slot.rotation_y || 0,
      1.0,
      'city',
      '3D'
    )
    const placedItem = response.data?.placed_item || null
    if (placedItem) {
      selectedDecoration.value = placedItem
      upsertPlacedDecoration(placedItem)
      inventoryStore.completePlacement(placedItem, placementItem.value)
    }
    isPlacementMode.value = false
    placementItem.value = null
    hoveredPlacementSlotId.value = ''
    await loadPlacedDecorations({
      preserveExisting: true,
      fallbackItem: placedItem,
      showRefreshError: Boolean(placedItem)
    })
  } catch (error) {
    window.alert(error.response?.data?.detail || 'Placement failed, please try again.')
  } finally {
    isPlacementSubmitting.value = false
  }
}

const deleteSelectedDecoration = async () => {
  if (!selectedDecoration.value) return
  const target = selectedDecoration.value
  if (!window.confirm(`确认移除 ${target.name_cn || target.name} 吗？`)) return
  try {
    await unifiedShopApi.removePlaced(target.id, currentUsername.value)
    inventoryStore.handlePlacedItemRemoval(target)
    await inventoryStore.refreshInventory(currentUsername.value)
    selectedDecoration.value = null
    await loadPlacedDecorations()
  } catch (error) {
    window.alert(error.response?.data?.detail || '移除失败，请稍后重试。')
  }
}

const selectDecoration = (item) => {
  if (isPlacementMode.value) return
  selectedDecoration.value = selectedDecoration.value?.id === item.id ? null : item
}

const consumePendingPlacement = () => {
  inventoryStore.consumeLegacyPendingPlacement()
}

watch(compatibleSlots, (slots) => {
  if (!isPlacementMode.value) return
  if (!slots.length) {
    hoveredPlacementSlotId.value = ''
    return
  }
  if (!slots.some((slot) => slot.slot_id === hoveredPlacementSlotId.value)) {
    hoveredPlacementSlotId.value = slots[0].slot_id
  }
})

watch(
  () => [inventoryStore.placementDraft, inventoryStore.placementMode, dimensionStore.activeDimension, citySlots.value.length],
  () => {
    syncPlacementModeFromStore()
  },
  { immediate: true }
)

watch(previewSlot, (slot) => {
  if (!slot || !placementItem.value || props.previewMode) return
  inventoryStore.updateGhostPreview({
    slotId: slot.slot_id,
    x: slot.x,
    y: getSafeCityY(slot.y),
    z: slot.z,
    rotationY: slot.rotation_y || 0
  })
})

const handleKeydown = (event) => {
  if (event.key === 'Escape' && isPlacementMode.value) {
    exitPlacementMode()
  }
  if (event.key === 'Delete' && selectedDecoration.value) {
    deleteSelectedDecoration()
  }
}


onMounted(async () => {
  supportsHover.value = window.matchMedia('(hover: hover) and (pointer: fine)').matches
  const bootstrapTasks = props.previewMode
    ? [loadCitySlots(), loadPlacedDecorations()]
    : [loadCitySlots(), loadPlacedDecorations(), loadUserGrowth()]
  await Promise.all(bootstrapTasks)
  if (!props.previewMode) {
    consumePendingPlacement()
    window.addEventListener('keydown', handleKeydown)
  }
})

onUnmounted(() => {
  if (!props.previewMode) {
    window.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<template>
  <div class="city-scene-page" :class="{ 'preview-mode': props.previewMode }">
    <div v-if="isPlacementMode && !props.previewMode" class="placement-banner kenney-hud-panel">
      <div class="placement-copy">
        <span class="placement-badge">{{ placementType === 'building' ? '建筑槽位' : '绿化槽位' }}</span>
        <strong>正在放置 {{ placementItem?.nameCn || placementItem?.name || placementItem?.name_cn || placementItem?.name }}</strong>
        <span>{{ isPlacementSubmitting ? '正在完成部署...' : '点击发光槽位即可完成放置' }}</span>
      </div>
      <button class="banner-btn kenney-hud-btn kenney-hud-btn--small kenney-hud-btn--danger" type="button" :disabled="isPlacementSubmitting" @click="exitPlacementMode">
        取消
      </button>
    </div>

    <div class="skyline-overlay">
      <div class="horizon"></div>
      <div class="orbital-ring orbital-ring-a"></div>
      <div class="orbital-ring orbital-ring-b"></div>
      <div class="city-haze"></div>
    </div>

    <div class="canvas-layer">
      <TresCanvas :clear-color="CITY_THEME.sky" :window-size="!props.previewMode">
        <TresPerspectiveCamera :position="[22, 16, 20]" :look-at="[0, 2.2, 0]" />
        <OrbitControls
          :enable-damping="true"
          :damping-factor="0.06"
          :min-distance="10"
          :max-distance="30"
          :max-polar-angle="Math.PI / 2.08"
        />

        <TresAmbientLight :color="CITY_THEME.ambient" :intensity="CITY_THEME.ambientIntensity" />
        <TresDirectionalLight :position="[10, 18, 8]" :color="CITY_THEME.directional" :intensity="CITY_THEME.directionalIntensity" />
        <TresDirectionalLight :position="[-10, 12, -6]" color="#6d5cff" :intensity="0.6" />

        <TresMesh :position="[0, -1.55, 0]" :rotation="[-Math.PI / 2, 0, 0]">
          <TresPlaneGeometry :args="[120, 120]" />
          <TresMeshStandardMaterial :color="CITY_THEME.fogPlane" />
        </TresMesh>

        <TresMesh :position="[0, -1.5, -16]">
          <TresBoxGeometry :args="[42, 10, 0.3]" />
          <TresMeshStandardMaterial color="#13203a" :emissive="CITY_THEME.horizonGlow" :emissive-intensity="0.18" :transparent="true" :opacity="0.35" />
        </TresMesh>

        <FloatingIsland :scale="1" theme="city" />

        <TresGroup
          v-if="isPlacementMode && placementItem && previewSlot"
          :position="[previewSlot.x, getSafeCityY(previewSlot.y), previewSlot.z]"
          :rotation="[0, ((previewSlot.rotation_y || 0) * Math.PI) / 180, 0]"
        >
          <CityModelInstance
            :item="placementItem"
            :ghost="true"
            :target-footprint="previewTargetFootprint"
          />
        </TresGroup>

        <TresGroup
          v-for="slot in compatibleSlots"
          :key="slot.slot_id"
          :position="[slot.x, getSafeCityY(slot.y) + 0.11, slot.z]"
        >
          <TresMesh
            :position="[0, 0.02, 0]"
            :rotation="[-Math.PI / 2, 0, 0]"
            :render-order="12"
            @pointerenter.stop="handleSlotPointerEnter(slot)"
            @pointermove.stop="handleSlotPointerEnter(slot)"
            @click.stop="handleSlotClick(slot)"
          >
            <TresCircleGeometry :args="[getSlotMarkerRadius(slot), 32]" />
            <TresMeshBasicMaterial
              :color="slot.slot_type === 'building' ? '#73e0ff' : '#53f0b0'"
              :transparent="true"
              :opacity="0.18"
              :depth-test="false"
              :depth-write="false"
            />
          </TresMesh>
          <TresMesh
            :position="[0, 0.48, 0]"
            :render-order="11"
            @pointerenter.stop="handleSlotPointerEnter(slot)"
            @pointermove.stop="handleSlotPointerEnter(slot)"
            @click.stop="handleSlotClick(slot)"
          >
            <TresCylinderGeometry :args="[slot.slot_type === 'building' ? 0.34 : 0.28, slot.slot_type === 'building' ? 0.18 : 0.14, 0.92, 24, 1, true]" />
            <TresMeshBasicMaterial
              :color="slot.slot_type === 'building' ? '#73e0ff' : '#53f0b0'"
              :transparent="true"
              :opacity="0.22"
              :depth-test="false"
              :depth-write="false"
            />
          </TresMesh>
          <TresMesh
            :position="[0, 0.05, 0]"
            :rotation="[-Math.PI / 2, 0, 0]"
            :render-order="13"
            @pointerenter.stop="handleSlotPointerEnter(slot)"
            @pointermove.stop="handleSlotPointerEnter(slot)"
            @click.stop="handleSlotClick(slot)"
          >
            <TresRingGeometry :args="getSlotRingArgs(slot)" />
            <TresMeshBasicMaterial
              :color="slot.slot_type === 'building' ? '#73e0ff' : '#53f0b0'"
              :transparent="true"
              :opacity="slot.slot_type === 'building' ? 0.92 : 0.86"
              :depth-test="false"
              :depth-write="false"
            />
          </TresMesh>
          <TresMesh
            :position="[0, 0.12, 0]"
            :render-order="14"
            @pointerenter.stop="handleSlotPointerEnter(slot)"
            @pointermove.stop="handleSlotPointerEnter(slot)"
            @click.stop="handleSlotClick(slot)"
          >
            <TresCylinderGeometry :args="[0.1, 0.1, 0.22, 12]" />
            <TresMeshBasicMaterial
              :color="slot.slot_type === 'building' ? '#73e0ff' : '#53f0b0'"
              :transparent="true"
              :opacity="0.95"
              :depth-test="false"
              :depth-write="false"
            />
          </TresMesh>
        </TresGroup>

        <PlacedModel
          v-for="deco in placedDecorations"
          :key="deco.id"
          :item="deco"
          :is-selected="selectedDecoration?.id === deco.id"
          :slot-footprint="slotFootprintById[deco.slot_id] || 0"
          @select="selectDecoration(deco)"
        />
      </TresCanvas>
    </div>

  </div>
</template>

<style scoped>
.city-scene-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 18%, rgba(109, 92, 255, 0.25), transparent 24%),
    radial-gradient(circle at 50% 34%, rgba(76, 222, 255, 0.18), transparent 30%),
    linear-gradient(180deg, #02050e 0%, #050914 42%, #0a1122 72%, #08101e 100%);
  color: #eef7ff;
}

.city-scene-page.preview-mode {
  width: 100%;
  height: 100%;
  border-radius: 18px;
  background:
    radial-gradient(circle at 50% 18%, rgba(109, 92, 255, 0.18), transparent 28%),
    radial-gradient(circle at 50% 34%, rgba(76, 222, 255, 0.14), transparent 30%),
    linear-gradient(180deg, #040814 0%, #08111f 48%, #0a192f 100%);
}

.canvas-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.skyline-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.horizon {
  position: absolute;
  left: 50%;
  bottom: 20%;
  width: min(80vw, 920px);
  height: 240px;
  transform: translateX(-50%);
  background:
    linear-gradient(180deg, rgba(79, 115, 255, 0.02), rgba(79, 115, 255, 0.14)),
    repeating-linear-gradient(
      90deg,
      rgba(125, 177, 255, 0.12) 0,
      rgba(125, 177, 255, 0.12) 14px,
      transparent 14px,
      transparent 34px
    );
  clip-path: polygon(0 100%, 2% 64%, 6% 64%, 6% 42%, 11% 42%, 11% 78%, 16% 78%, 16% 30%, 22% 30%, 22% 70%, 29% 70%, 29% 24%, 36% 24%, 36% 84%, 41% 84%, 41% 44%, 48% 44%, 48% 18%, 54% 18%, 54% 74%, 62% 74%, 62% 36%, 69% 36%, 69% 62%, 76% 62%, 76% 26%, 83% 26%, 83% 72%, 90% 72%, 90% 54%, 95% 54%, 95% 100%);
  filter: drop-shadow(0 0 36px rgba(109, 92, 255, 0.3));
}

.orbital-ring {
  position: absolute;
  border-radius: 999px;
  border: 1px solid rgba(115, 224, 255, 0.16);
}

.orbital-ring-a {
  width: 620px;
  height: 620px;
  top: -230px;
  left: 50%;
  transform: translateX(-50%);
}

.orbital-ring-b {
  width: 760px;
  height: 760px;
  top: -300px;
  left: 50%;
  transform: translateX(-50%) rotate(18deg);
  border-color: rgba(109, 92, 255, 0.16);
}

.city-haze {
  position: absolute;
  left: 50%;
  bottom: 16%;
  width: min(90vw, 1040px);
  height: 220px;
  transform: translateX(-50%);
  background: radial-gradient(circle, rgba(76, 222, 255, 0.16), transparent 64%);
  filter: blur(26px);
}

.placement-banner {
  position: fixed;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 12;
  width: min(640px, calc(100vw - 24px));
  padding: 12px 16px;
  border-radius: 20px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.placement-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.placement-badge {
  display: inline-flex;
  width: fit-content;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(76, 222, 255, 0.12);
  font-size: 11px;
  font-weight: 700;
}

.banner-btn {
  min-width: 84px;
}

.selected-bar {
  position: fixed;
  left: 50%;
  bottom: 82px;
  transform: translateX(-50%);
  z-index: 10;
  min-width: 280px;
  max-width: calc(100vw - 24px);
  border-radius: 20px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.selected-name {
  font-weight: 800;
}

.selected-slot {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.72);
}

.selected-btn {
  margin-left: auto;
  border: none;
  border-radius: 12px;
  padding: 9px 14px;
  background: rgba(255, 255, 255, 0.08);
  color: #eef7ff;
  cursor: pointer;
}

.selected-btn.danger {
  margin-left: 0;
  background: rgba(255, 101, 133, 0.16);
}

@media (max-width: 768px) {
  .selected-bar {
    bottom: 158px;
    padding: 12px;
    flex-wrap: wrap;
  }
}
</style>




