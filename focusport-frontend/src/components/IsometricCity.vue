<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { unifiedShopApi } from '../api'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'
import '../assets/kenney-ui/kenney-hud.css'

const router = useRouter()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()

const username = ref(localStorage.getItem('username') || 'guest')
const stageRef = ref(null)
const manifest = ref({
  grid: {
    cols: 20,
    rows: 20,
    tile_width: 96,
    tile_height: 48
  },
  items: []
})

const selectedPlacedId = ref('')
const hoveredCell = ref(null)
const feedback = ref('')
const isLoading = ref(false)
const isSubmitting = ref(false)
const GAIA_VISUAL_V2_KEY = 'gaiaVisualV2'
const gaiaVisualV2 = ref(true)

const zoomScale = ref(1)
const baseFitScale = ref(1)
const ZOOM_MIN = 0.25
const ZOOM_MAX = 2.0
const ZOOM_STEP = 0.15

const gridConfig = computed(() => manifest.value.grid || { cols: 20, rows: 20, tile_width: 96, tile_height: 48 })
const tileWidth = computed(() => Number(gridConfig.value.tile_width || 96))
const tileHeight = computed(() => Number(gridConfig.value.tile_height || 48))
const originX = computed(() => gridConfig.value.rows * (tileWidth.value / 2) + 140)
const originY = computed(() => 120)
const sceneWidth = computed(() => (gridConfig.value.cols + gridConfig.value.rows) * (tileWidth.value / 2) + 320)
const sceneHeight = computed(() => (gridConfig.value.cols + gridConfig.value.rows) * (tileHeight.value / 2) + 420)

const gaiaPlacedItems = computed(() => inventoryStore.placedByDimension.GAIA || [])
const activePlacementItem = computed(() => (
  inventoryStore.isPlacingGaia ? inventoryStore.placementDraft : null
))

const selectedPlacedItem = computed(() => (
  gaiaPlacedItems.value.find((item) => item.id === selectedPlacedId.value) || null
))

const placementFootprint = computed(() => ({
  width: Math.max(1, Number(activePlacementItem.value?.gridWidth || activePlacementItem.value?.footprint?.width || 1)),
  height: Math.max(1, Number(activePlacementItem.value?.gridHeight || activePlacementItem.value?.footprint?.height || 1))
}))

const previewValid = computed(() => {
  if (!hoveredCell.value || !activePlacementItem.value) return false
  return canPlaceAt(hoveredCell.value.x, hoveredCell.value.y)
})

const previewCells = computed(() => {
  if (!hoveredCell.value || !activePlacementItem.value) return []
  return footprintCellsFor(hoveredCell.value.x, hoveredCell.value.y, placementFootprint.value.width, placementFootprint.value.height)
})

const gridCells = computed(() => {
  const cells = []
  for (let y = 0; y < gridConfig.value.rows; y += 1) {
    for (let x = 0; x < gridConfig.value.cols; x += 1) {
      cells.push({ x, y, key: `${x}-${y}` })
    }
  }
  return cells
})

const readGaiaVisualV2Flag = () => {
  if (typeof window === 'undefined') return true
  const raw = window.localStorage.getItem(GAIA_VISUAL_V2_KEY)
  if (raw === null) return true
  const normalized = String(raw).trim().toLowerCase()
  return !['0', 'false', 'off', 'legacy'].includes(normalized)
}

const syncGaiaVisualV2 = () => {
  gaiaVisualV2.value = readGaiaVisualV2Flag()
}

const roadAxes = computed(() => {
  const middle = Math.floor(gridConfig.value.cols / 2)
  return new Set([middle - 1, middle, middle + 1])
})

const isRoadCell = (x, y) => (
  roadAxes.value.has(x) || roadAxes.value.has(y)
)

const isIntersectionCell = (x, y) => (
  roadAxes.value.has(x) && roadAxes.value.has(y)
)

const isCrosswalkCell = (x, y) => {
  if (isIntersectionCell(x, y)) return false
  const roadEvery = 5
  if (roadAxes.value.has(x)) {
    return y % roadEvery === 0
  }
  if (roadAxes.value.has(y)) {
    return x % roadEvery === 0
  }
  return false
}

const cellVisualClasses = (cell) => ({
  road: isRoadCell(cell.x, cell.y),
  intersection: isIntersectionCell(cell.x, cell.y),
  crosswalk: isCrosswalkCell(cell.x, cell.y)
})

const toIso = (x, y) => ({
  left: originX.value + (x - y) * (tileWidth.value / 2),
  top: originY.value + (x + y) * (tileHeight.value / 2)
})

const screenToGrid = (clientX, clientY) => {
  if (!stageRef.value) return null
  const stageEl = stageRef.value
  const rect = stageEl.getBoundingClientRect()
  const localX = clientX - rect.left + stageEl.scrollLeft
  const localY = clientY - rect.top + stageEl.scrollTop
  const sceneX = localX / zoomScale.value
  const sceneY = localY / zoomScale.value
  const normalizedX = (sceneX - originX.value) / (tileWidth.value / 2)
  const normalizedY = (sceneY - originY.value) / (tileHeight.value / 2)
  const gridX = Math.floor((normalizedY + normalizedX) / 2)
  const gridY = Math.floor((normalizedY - normalizedX) / 2)

  return {
    x: gridX,
    y: gridY,
    localX: sceneX,
    localY
  }
}

const isInsideGrid = (x, y, width = 1, height = 1) => (
  x >= 0 &&
  y >= 0 &&
  x + width <= gridConfig.value.cols &&
  y + height <= gridConfig.value.rows
)

const rectanglesOverlap = (ax, ay, aw, ah, bx, by, bw, bh) => (
  ax < bx + bw &&
  ax + aw > bx &&
  ay < by + bh &&
  ay + ah > by
)

const footprintCellsFor = (anchorX, anchorY, width, height) => {
  const cells = []
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      cells.push({ x: anchorX + x, y: anchorY + y })
    }
  }
  return cells
}

const isOccupied = (anchorX, anchorY, width, height) => gaiaPlacedItems.value.some((item) => (
  rectanglesOverlap(
    anchorX,
    anchorY,
    width,
    height,
    Number(item.position?.gridX || 0),
    Number(item.position?.gridY || 0),
    Math.max(1, Number(item.footprint?.width || 1)),
    Math.max(1, Number(item.footprint?.height || 1))
  )
))

const canPlaceAt = (anchorX, anchorY) => {
  if (!activePlacementItem.value) return false
  return (
    isInsideGrid(anchorX, anchorY, placementFootprint.value.width, placementFootprint.value.height) &&
    !isOccupied(anchorX, anchorY, placementFootprint.value.width, placementFootprint.value.height)
  )
}

const loadManifest = async () => {
  try {
    const response = await fetch('/assets/2d/manifest.json')
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    manifest.value = await response.json()
  } catch (error) {
    console.error('Failed to load GAIA manifest', error)
    feedback.value = 'GAIA 资产清单暂时不可用，但背包与商店仍可继续访问。'
  }
}

const gridCellStyle = (cell) => {
  const point = toIso(cell.x, cell.y)
  return {
    left: `${point.left}px`,
    top: `${point.top}px`,
    width: `${tileWidth.value}px`,
    height: `${tileHeight.value}px`
  }
}

const footprintStyle = (cell) => {
  const point = toIso(cell.x, cell.y)
  return {
    left: `${point.left}px`,
    top: `${point.top}px`
  }
}

const placedItemStyle = (item) => {
  const anchorX = Number(item.position?.gridX || 0)
  const anchorY = Number(item.position?.gridY || 0)
  const width = Math.max(1, Number(item.footprint?.width || 1))
  const height = Math.max(1, Number(item.footprint?.height || 1))
  const centerX = anchorX + (width - 1) / 2
  const centerY = anchorY + (height - 1) / 2
  const point = toIso(centerX, centerY)
  return {
    left: `${point.left}px`,
    top: `${point.top}px`
  }
}

const previewSpriteStyle = computed(() => {
  if (!hoveredCell.value || !activePlacementItem.value) return null
  const centerX = hoveredCell.value.x + (placementFootprint.value.width - 1) / 2
  const centerY = hoveredCell.value.y + (placementFootprint.value.height - 1) / 2
  const point = toIso(centerX, centerY)
  return {
    left: `${point.left}px`,
    top: `${point.top}px`
  }
})

const handleScenePointerMove = (event) => {
  const nextCell = screenToGrid(event.clientX, event.clientY)
  if (!nextCell) return
  hoveredCell.value = nextCell
}

const clearHoveredCell = () => {
  hoveredCell.value = null
  if (activePlacementItem.value) {
    inventoryStore.updateGhostPreview({ gridX: null, gridY: null, valid: false })
  }
}

const placeCurrentItem = async () => {
  if (!activePlacementItem.value || !hoveredCell.value || isSubmitting.value) return
  if (!previewValid.value) {
    feedback.value = '当前格点被占用，或已经超出 20x20 GAIA 网格边界。'
    return
  }

  isSubmitting.value = true
  feedback.value = ''
  try {
    const response = await unifiedShopApi.place(
      username.value,
      activePlacementItem.value.itemId,
      null,
      hoveredCell.value.x,
      0,
      hoveredCell.value.y,
      0,
      1,
      'isometric-city',
      '2D',
      hoveredCell.value.x,
      hoveredCell.value.y
    )
    const placedItem = inventoryStore.completePlacement(response.data?.placed_item, activePlacementItem.value)
    selectedPlacedId.value = placedItem.id
    feedback.value = `${placedItem.nameCn || placedItem.name} 已部署到 GAIA 网格 ${hoveredCell.value.x}, ${hoveredCell.value.y}。`
  } catch (error) {
    feedback.value = error.response?.data?.detail || 'GAIA 放置失败，请稍后再试。'
  } finally {
    isSubmitting.value = false
  }
}

const removeSelectedPlacedItem = async () => {
  if (!selectedPlacedItem.value) return
  if (!window.confirm(`确认移除 ${selectedPlacedItem.value.nameCn || selectedPlacedItem.value.name} 吗？`)) {
    return
  }

  try {
    await unifiedShopApi.removePlaced(selectedPlacedItem.value.id, username.value)
    inventoryStore.handlePlacedItemRemoval(selectedPlacedItem.value)
    await inventoryStore.refreshInventory(username.value)
    selectedPlacedId.value = ''
    feedback.value = '该建筑已回收到背包。'
  } catch (error) {
    feedback.value = error.response?.data?.detail || '移除失败，请稍后再试。'
  }
}

const openShop = () => {
  dimensionStore.setDimension('GAIA')
  router.push('/shop')
}
const switchToPhysical = () => dimensionStore.playDimensionTransition('PHYSICAL')

watch([activePlacementItem, hoveredCell], () => {
  if (!activePlacementItem.value || !hoveredCell.value) return
  inventoryStore.updateGhostPreview({
    gridX: hoveredCell.value.x,
    gridY: hoveredCell.value.y,
    valid: previewValid.value
  })
})

watch(activePlacementItem, (nextItem) => {
  if (!nextItem) {
    feedback.value = ''
    return
  }
  feedback.value = `正在为 ${nextItem.nameCn || nextItem.name} 准备盖亚演算舱放置。`
})

const computeFitScale = () => {
  if (!stageRef.value) return 1
  const stageEl = stageRef.value
  const style = getComputedStyle(stageEl)
  const padX = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)
  const padY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom)
  const availW = stageEl.clientWidth - padX
  const availH = stageEl.clientHeight - padY
  if (availW <= 0 || availH <= 0) return 1
  const scaleX = availW / sceneWidth.value
  const scaleY = availH / sceneHeight.value
  return Math.min(scaleX, scaleY, 1)
}

let resizeObserver = null

const recalcFitScale = () => {
  const fit = computeFitScale()
  const oldBase = baseFitScale.value
  baseFitScale.value = fit
  if (Math.abs(zoomScale.value - oldBase) < 0.001) {
    zoomScale.value = fit
  }
}

const zoomIn = () => {
  zoomScale.value = Math.min(zoomScale.value + ZOOM_STEP, ZOOM_MAX)
}

const zoomOut = () => {
  zoomScale.value = Math.max(zoomScale.value - ZOOM_STEP, ZOOM_MIN)
}

const zoomReset = () => {
  zoomScale.value = baseFitScale.value
}

const handleStageWheel = (event) => {
  if (!event.ctrlKey && !event.metaKey) return
  event.preventDefault()
  const delta = event.deltaY > 0 ? -ZOOM_STEP * 0.5 : ZOOM_STEP * 0.5
  zoomScale.value = Math.max(ZOOM_MIN, Math.min(zoomScale.value + delta, ZOOM_MAX))
}

const handleStorageSync = (event) => {
  if (!event || event.key === GAIA_VISUAL_V2_KEY) {
    syncGaiaVisualV2()
  }
}

onMounted(async () => {
  syncGaiaVisualV2()
  window.addEventListener('storage', handleStorageSync)
  isLoading.value = true
  await Promise.all([
    loadManifest(),
    inventoryStore.refreshPlacedItems(username.value)
  ])
  isLoading.value = false
  await nextTick()
  recalcFitScale()
  if (stageRef.value) {
    resizeObserver = new ResizeObserver(() => recalcFitScale())
    resizeObserver.observe(stageRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('storage', handleStorageSync)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<template>
  <div class="iso-page iso-page-v2">
    <div class="iso-stage-wrap iso-stage-wrap-v2">
      <div v-if="isLoading" class="stage-loading kenney-hud-panel">正在同步 GAIA 网格...</div>

      <template v-else>
        <div class="zoom-bar zoom-bar-v2">
          <button type="button" class="zoom-btn" :disabled="zoomScale <= ZOOM_MIN" @click="zoomOut">&minus;</button>
          <span class="zoom-label">{{ Math.round(zoomScale * 100) }}%</span>
          <button type="button" class="zoom-btn" :disabled="zoomScale >= ZOOM_MAX" @click="zoomIn">&plus;</button>
          <button type="button" class="zoom-btn reset" @click="zoomReset">适配</button>
        </div>

        <div
          ref="stageRef"
          class="iso-stage kenney-hud-panel iso-stage-v2"
          @mousemove="handleScenePointerMove"
          @mouseleave="clearHoveredCell"
          @click="placeCurrentItem"
          @wheel="handleStageWheel"
        >
          <div
            class="scene-surface-wrapper"
            :style="{
              width: `${sceneWidth * zoomScale}px`,
              height: `${sceneHeight * zoomScale}px`
            }"
          >
            <div
              class="scene-surface"
              :style="{
                width: `${sceneWidth}px`,
                height: `${sceneHeight}px`,
                transform: `scale(${zoomScale})`,
                transformOrigin: 'top left'
              }"
            >
              <div
                v-for="cell in gridCells"
                :key="cell.key"
                class="iso-cell"
                :class="[{ hovered: hoveredCell?.x === cell.x && hoveredCell?.y === cell.y }, cellVisualClasses(cell)]"
                :style="gridCellStyle(cell)"
              >
                <span class="grid-index">{{ cell.x }},{{ cell.y }}</span>
              </div>

              <div
                v-for="cell in previewCells"
                :key="`preview-${cell.x}-${cell.y}`"
                class="preview-footprint"
                :class="{ invalid: !previewValid }"
                :style="footprintStyle(cell)"
              ></div>

              <button
                v-if="activePlacementItem && previewSpriteStyle"
                type="button"
                class="placed-sprite ghost"
                :class="{ invalid: !previewValid }"
                :style="previewSpriteStyle"
                @click.stop="placeCurrentItem"
              >
                <img
                  :src="activePlacementItem.previewPath || activePlacementItem.spritePath"
                  :alt="activePlacementItem.nameCn || activePlacementItem.name"
                />
                <span class="placed-label">{{ activePlacementItem.nameCn || activePlacementItem.name }}</span>
              </button>

              <button
                v-for="item in gaiaPlacedItems"
                :key="item.id"
                type="button"
                class="placed-sprite"
                :class="{ selected: selectedPlacedId === item.id, vehicle: item.subcategory === 'vehicles' }"
                :style="placedItemStyle(item)"
                @click.stop="selectedPlacedId = item.id"
              >
                <img :src="item.spritePath || item.previewPath || item.assetPath" :alt="item.nameCn || item.name" />
                <span class="placed-label">{{ item.nameCn || item.name }}</span>
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.iso-page {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  padding: 0;
  overflow: hidden;
  background: transparent;
}

.iso-stage-wrap {
  position: fixed;
  inset: 0;
}

.iso-stage-wrap .stage-loading,
.iso-stage-wrap .iso-stage {
  min-height: 100vh;
  height: 100vh;
  border-radius: 0;
}

.stage-loading {
  display: grid;
  place-items: center;
  font-size: 18px;
  color: #eef7ff;
}

.iso-stage {
  overflow: auto;
  padding: 12px;
  background: transparent;
}

.scene-surface-wrapper {
  position: relative;
  margin: 0 auto;
  overflow: visible;
}

.scene-surface {
  position: absolute;
  top: 0;
  left: 0;
}

.iso-cell,
.preview-footprint,
.placed-sprite {
  position: absolute;
  transform: translate(-50%, -50%);
}

.iso-cell {
  pointer-events: none;
}

.iso-cell::before,
.preview-footprint {
  content: '';
  width: 100%;
  height: 100%;
  display: block;
  clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
}

.iso-cell::before {
  background:
    linear-gradient(180deg, rgba(20, 35, 55, 0.92), rgba(12, 24, 42, 0.94)),
    #0e1e32;
  border: 1px solid rgba(115, 224, 255, 0.12);
  box-shadow: 0 7px 16px rgba(0, 0, 0, 0.3);
}

.iso-cell.hovered::before {
  box-shadow: 0 0 0 1px rgba(115, 224, 255, 0.5), 0 0 28px rgba(47, 216, 255, 0.25);
}

.iso-cell.road::before {
  background:
    linear-gradient(180deg, rgba(14, 22, 36, 0.98), rgba(8, 16, 28, 0.98)),
    #0a1420;
  border: 1px solid rgba(115, 224, 255, 0.08);
}

.iso-cell.intersection::before {
  background:
    linear-gradient(180deg, rgba(12, 20, 32, 0.98), rgba(6, 14, 24, 0.98)),
    #081220;
}

.iso-cell.road::after {
  content: '';
  position: absolute;
  inset: 36% 23%;
  transform: skewY(-27deg) rotate(45deg);
  border-radius: 999px;
  background: rgba(115, 224, 255, 0.3);
  box-shadow: 0 0 7px rgba(115, 224, 255, 0.2);
  pointer-events: none;
}

.iso-cell.intersection::after {
  background: rgba(115, 224, 255, 0.12);
}

.iso-cell.crosswalk::after {
  background: repeating-linear-gradient(
    90deg,
    rgba(242, 248, 255, 0.78) 0,
    rgba(242, 248, 255, 0.78) 8%,
    transparent 8%,
    transparent 16%
  );
  inset: 33% 16%;
}

.grid-index {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 10px;
  color: rgba(115, 224, 255, 0.35);
}

.preview-footprint {
  width: 96px;
  height: 48px;
  background: rgba(61, 235, 167, 0.36);
  box-shadow: 0 0 22px rgba(61, 235, 167, 0.26);
  pointer-events: none;
}

.preview-footprint.invalid {
  background: rgba(255, 106, 112, 0.38);
  box-shadow: 0 0 22px rgba(255, 106, 112, 0.24);
}

.placed-sprite {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
  transform: translate(-50%, calc(-100% + 18px));
}

.placed-sprite img {
  width: 120px;
  image-rendering: pixelated;
  filter: saturate(1.06) brightness(1.02) drop-shadow(0 10px 18px rgba(22, 36, 52, 0.36));
}

.placed-sprite.vehicle img {
  width: 72px;
}

.placed-sprite.ghost {
  opacity: 0.72;
}

.placed-sprite.ghost.invalid img {
  filter: saturate(0.75) brightness(0.92) hue-rotate(-32deg) drop-shadow(0 0 18px rgba(255, 114, 141, 0.28));
}

.placed-sprite.selected img {
  filter: saturate(1.12) brightness(1.06) drop-shadow(0 0 14px rgba(86, 173, 255, 0.7));
}

.placed-label {
  display: block;
  margin-top: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(7, 16, 34, 0.85);
  font-size: 11px;
  color: #dff4ff;
  white-space: nowrap;
  border: 1px solid rgba(115, 224, 255, 0.2);
}

.zoom-bar {
  position: fixed;
  top: 14px;
  right: 14px;
  z-index: 6;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(7, 16, 34, 0.9);
  border: 1px solid rgba(115, 224, 255, 0.3);
}

.zoom-btn {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 1px solid rgba(115, 224, 255, 0.2);
  background: rgba(255, 255, 255, 0.06);
  color: #eef7ff;
  font-size: 18px;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: background 0.15s ease;
}

.zoom-btn:hover:not(:disabled) {
  background: rgba(47, 216, 255, 0.16);
}

.zoom-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.zoom-btn.reset {
  width: auto;
  padding: 0 14px;
  font-size: 13px;
}

.zoom-label {
  min-width: 48px;
  text-align: center;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: rgba(156, 230, 255, 0.84);
}

@media (max-width: 768px) {
  .zoom-bar {
    top: 10px;
    right: 10px;
  }
}
</style>
