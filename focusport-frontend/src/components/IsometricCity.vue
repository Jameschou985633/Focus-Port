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
    feedback.value = '该全息建筑已回收到背包。'
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
  feedback.value = `正在为 ${nextItem.nameCn || nextItem.name} 准备 GAIA 全息放置。`
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

onMounted(async () => {
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
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<template>
  <div class="iso-page">
    <header class="iso-header kenney-hud-panel">
      <div class="header-copy">
        <span class="eyebrow">EARTH SIMULATOR · GAIA</span>
        <h1>GAIA 等距投影城市</h1>
        <p>20x20 等距网格已上线。鼠标位置会实时换算成 Grid X / Grid Y，并把全息资产吸附到网格中心。</p>
      </div>

      <div class="header-actions">
        <div class="metric-chip">
          <span>维度</span>
          <strong>{{ dimensionStore.currentDimensionLabel }}</strong>
        </div>
        <div class="metric-chip" v-if="hoveredCell">
          <span>光标</span>
          <strong>{{ hoveredCell.x }}, {{ hoveredCell.y }}</strong>
        </div>
        <button type="button" class="ghost-btn" @click="openShop">打开商店</button>
        <button type="button" class="ghost-btn accent" @click="switchToPhysical">切换到 PHYSICAL</button>
      </div>
    </header>

    <section class="iso-layout">
      <aside class="command-panel kenney-hud-panel">
        <div class="panel-block">
          <span class="panel-label">网格状态</span>
          <strong>{{ gridConfig.cols }} x {{ gridConfig.rows }}</strong>
          <p>屏幕坐标会在当前等距平面上反算成网格坐标，再做占地与重叠校验。</p>
        </div>

        <div class="panel-block">
          <span class="panel-label">放置状态</span>
          <template v-if="activePlacementItem">
            <strong>{{ activePlacementItem.nameCn || activePlacementItem.name }}</strong>
            <p>占地 {{ placementFootprint.width }} x {{ placementFootprint.height }}</p>
            <p>{{ previewValid ? '当前位置可部署' : '当前位置不可部署' }}</p>
            <button type="button" class="panel-btn" @click="inventoryStore.cancelPlacement()">取消放置</button>
          </template>
          <template v-else>
            <strong>等待背包指令</strong>
            <p>从右下角背包选择一个 GAIA 资产，幽灵预览就会跟随鼠标进入部署模式。</p>
          </template>
        </div>

        <div class="panel-block">
          <span class="panel-label">已选全息资产</span>
          <template v-if="selectedPlacedItem">
            <strong>{{ selectedPlacedItem.nameCn || selectedPlacedItem.name }}</strong>
            <p>Grid {{ selectedPlacedItem.position.gridX }}, {{ selectedPlacedItem.position.gridY }}</p>
            <button type="button" class="panel-btn danger" @click="removeSelectedPlacedItem">移回背包</button>
          </template>
          <template v-else>
            <strong>暂无选中资产</strong>
            <p>点击场景中的已放置建筑或车辆，可以查看并回收到背包。</p>
          </template>
        </div>

        <p v-if="feedback" class="feedback-line">{{ feedback }}</p>
      </aside>

      <div class="iso-stage-wrap">
        <div v-if="isLoading" class="stage-loading kenney-hud-panel">正在同步 GAIA 全息网格...</div>

        <template v-else>
          <div class="zoom-bar">
            <button type="button" class="zoom-btn" :disabled="zoomScale <= ZOOM_MIN" @click="zoomOut">&minus;</button>
            <span class="zoom-label">{{ Math.round(zoomScale * 100) }}%</span>
            <button type="button" class="zoom-btn" :disabled="zoomScale >= ZOOM_MAX" @click="zoomIn">&plus;</button>
            <button type="button" class="zoom-btn reset" @click="zoomReset">适配</button>
          </div>

          <div
            ref="stageRef"
            class="iso-stage kenney-hud-panel"
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
                  :class="{ hovered: hoveredCell?.x === cell.x && hoveredCell?.y === cell.y }"
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
    </section>
  </div>
</template>

<style scoped>
.iso-page {
  min-height: 100vh;
  padding: 18px;
  box-sizing: border-box;
  color: #eef7ff;
  background:
    radial-gradient(circle at 20% 16%, rgba(47, 216, 255, 0.12), transparent 18%),
    radial-gradient(circle at 82% 12%, rgba(109, 92, 255, 0.16), transparent 20%),
    linear-gradient(180deg, #081526 0%, #0a192f 100%);
}

.iso-header,
.command-panel,
.iso-stage {
  border-radius: 24px;
}

.iso-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
  padding: 18px 20px;
}

.eyebrow,
.panel-label {
  display: block;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: rgba(156, 230, 255, 0.84);
  text-transform: uppercase;
}

.header-copy h1 {
  margin: 8px 0 6px;
  font-size: 32px;
}

.header-copy p,
.panel-block p {
  margin: 0;
  color: rgba(230, 246, 255, 0.72);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.metric-chip,
.ghost-btn,
.panel-btn {
  min-height: 42px;
  border-radius: 999px;
  padding: 0 16px;
  border: 1px solid rgba(115, 224, 255, 0.2);
  background: rgba(8, 16, 30, 0.7);
  color: #eef7ff;
}

.metric-chip {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
}

.metric-chip span {
  font-size: 11px;
  color: rgba(230, 246, 255, 0.68);
}

.ghost-btn,
.panel-btn {
  cursor: pointer;
}

.ghost-btn.accent,
.panel-btn {
  background: linear-gradient(180deg, #2fd8ff, #2d74ff);
  border-color: transparent;
}

.panel-btn.danger {
  background: linear-gradient(180deg, #ff728d, #e3446c);
}

.iso-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
}

.command-panel {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-block {
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
}

.panel-block strong {
  display: block;
  margin: 6px 0 8px;
  font-size: 20px;
}

.feedback-line {
  margin: 0;
  color: #9ce6ff;
}

.iso-stage-wrap {
  min-width: 0;
}

.stage-loading,
.iso-stage {
  min-height: max(400px, calc(100vh - 220px));
  padding: 18px;
}

.stage-loading {
  display: grid;
  place-items: center;
  font-size: 18px;
}

.iso-stage {
  overflow: auto;
  background:
    radial-gradient(circle at 50% 0%, rgba(47, 216, 255, 0.08), transparent 40%),
    linear-gradient(180deg, rgba(10, 25, 47, 0.92), rgba(6, 11, 22, 0.96));
}

.scene-surface-wrapper {
  position: relative;
  margin: 0 auto;
  overflow: hidden;
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
    linear-gradient(180deg, rgba(229, 234, 247, 0.94), rgba(191, 204, 224, 0.84)),
    #d8deea;
  border: 1px solid rgba(12, 27, 59, 0.26);
  box-shadow: 0 12px 18px rgba(0, 0, 0, 0.16);
}

.iso-cell.hovered::before {
  box-shadow: 0 0 0 1px rgba(115, 224, 255, 0.46), 0 0 28px rgba(47, 216, 255, 0.18);
}

.grid-index {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 10px;
  color: rgba(8, 16, 30, 0.44);
}

.preview-footprint {
  width: 96px;
  height: 48px;
  background: rgba(47, 216, 255, 0.26);
  box-shadow: 0 0 18px rgba(47, 216, 255, 0.14);
  pointer-events: none;
}

.preview-footprint.invalid {
  background: rgba(255, 114, 141, 0.28);
  box-shadow: 0 0 18px rgba(255, 114, 141, 0.14);
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
  mix-blend-mode: screen;
  filter: hue-rotate(178deg) saturate(1.25) brightness(1.16) drop-shadow(0 18px 26px rgba(0, 0, 0, 0.28)) drop-shadow(0 0 14px rgba(88, 228, 255, 0.22));
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
  filter: hue-rotate(178deg) saturate(1.25) brightness(1.16) drop-shadow(0 0 18px rgba(47, 216, 255, 0.45));
}

.placed-label {
  display: block;
  margin-top: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(7, 16, 34, 0.72);
  font-size: 11px;
  color: #dff4ff;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .iso-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .iso-page {
    padding: 12px;
    padding-bottom: 240px;
  }

  .iso-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .zoom-bar {
    position: sticky;
    top: 0;
    z-index: 4;
  }
}

.zoom-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(8, 18, 44, 0.92);
  border: 1px solid rgba(115, 224, 255, 0.18);
  width: fit-content;
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
</style>
