<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { unifiedShopApi } from '../api'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'
import '../assets/kenney-ui/kenney-hud.css'

const router = useRouter()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()

const username = ref(localStorage.getItem('username') || 'guest')
const selectedPlacedId = ref('')
const hoveredLotKey = ref('')
const feedback = ref('')
const isLoading = ref(false)
const isSubmitting = ref(false)
const recentlyPlacedIds = ref(new Set())

/* responsive viewport scaling */
const viewportWidth = ref(window.innerWidth)
const viewportHeight = ref(window.innerHeight)
let resizeRaf = null
const onResize = () => {
  if (resizeRaf) return
  resizeRaf = requestAnimationFrame(() => {
    viewportWidth.value = window.innerWidth
    viewportHeight.value = window.innerHeight
    resizeRaf = null
  })
}

const gridConfig = {
  cols: 20,
  rows: 20,
  tileWidth: 96,
  tileHeight: 48
}

const buildLots = [
  { key: 'lot-1', x: 4, y: 4, label: '晨光地块' },
  { key: 'lot-2', x: 8, y: 3, label: '云桥地块' },
  { key: 'lot-3', x: 13, y: 4, label: '星港地块' },
  { key: 'lot-4', x: 5, y: 9, label: '花园地块' },
  { key: 'lot-5', x: 10, y: 8, label: '中心地块' },
  { key: 'lot-6', x: 15, y: 10, label: '湖畔地块' },
  { key: 'lot-7', x: 7, y: 14, label: '谷仓地块' },
  { key: 'lot-8', x: 12, y: 15, label: '灯塔地块' },
  { key: 'lot-9', x: 16, y: 6, label: '东岸地块' },
  { key: 'lot-10', x: 3, y: 13, label: '西岸地块' }
]

const originX = computed(() => gridConfig.rows * (gridConfig.tileWidth / 2) + 160)
const originY = computed(() => 130)
const sceneWidth = computed(() => (gridConfig.cols + gridConfig.rows) * (gridConfig.tileWidth / 2) + 360)
const sceneHeight = computed(() => (gridConfig.cols + gridConfig.rows) * (gridConfig.tileHeight / 2) + 430)

const gaiaPlacedItems = computed(() => inventoryStore.placedByDimension.GAIA || [])
const activePlacementItem = computed(() => (inventoryStore.isPlacingGaia ? inventoryStore.placementDraft : null))
const hoveredLot = computed(() => buildLots.find((lot) => lot.key === hoveredLotKey.value) || null)
const selectedPlacedItem = computed(() => gaiaPlacedItems.value.find((item) => String(item.id) === String(selectedPlacedId.value)) || null)

const sceneScale = computed(() => {
  const vw = viewportWidth.value
  const vh = viewportHeight.value
  const scaleX = (vw - 160) / sceneWidth.value
  const scaleY = (vh - 200) / sceneHeight.value
  return Math.max(0.4, Math.min(1, scaleX, scaleY))
})

const selectedLotKey = computed(() => {
  if (!selectedPlacedItem.value) return ''
  const sx = Number(selectedPlacedItem.value.position?.gridX ?? selectedPlacedItem.value.grid_x ?? 0)
  const sy = Number(selectedPlacedItem.value.position?.gridY ?? selectedPlacedItem.value.grid_y ?? 0)
  const match = buildLots.find(lot => lot.x === sx && lot.y === sy)
  return match?.key || ''
})

const occupiedLotCount = computed(() => buildLots.filter(lot => isLotOccupied(lot)).length)
const availableLotCount = computed(() => buildLots.filter(lot => !isLotOccupied(lot)).length)

const placementFootprint = computed(() => ({
  width: Math.max(1, Number(activePlacementItem.value?.gridWidth || activePlacementItem.value?.footprint?.width || 1)),
  height: Math.max(1, Number(activePlacementItem.value?.gridHeight || activePlacementItem.value?.footprint?.height || 1))
}))

const toIso = (x, y) => ({
  left: originX.value + (x - y) * (gridConfig.tileWidth / 2),
  top: originY.value + (x + y) * (gridConfig.tileHeight / 2)
})

/* grid underlay helpers */
const hw = gridConfig.tileWidth / 2
const hh = gridConfig.tileHeight / 2
const tilePolygonPoints = (x, y) => {
  const cx = originX.value + (x - y) * hw
  const cy = originY.value + (x + y) * hh
  return `${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`
}
const isBuildArea = (x, y) => buildLots.some(lot => lot.x === x && lot.y === y)

const rectanglesOverlap = (ax, ay, aw, ah, bx, by, bw, bh) => (
  ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by
)

const isInsideGrid = (x, y, width = 1, height = 1) => (
  x >= 0 && y >= 0 && x + width <= gridConfig.cols && y + height <= gridConfig.rows
)

const isOccupied = (anchorX, anchorY, width = 1, height = 1) => gaiaPlacedItems.value.some((item) => (
  rectanglesOverlap(
    anchorX,
    anchorY,
    width,
    height,
    Number(item.position?.gridX || item.grid_x || 0),
    Number(item.position?.gridY || item.grid_y || 0),
    Math.max(1, Number(item.footprint?.width || item.grid_width || 1)),
    Math.max(1, Number(item.footprint?.height || item.grid_height || 1))
  )
))

const isLotOccupied = (lot) => isOccupied(lot.x, lot.y, 1, 1)

const canPlaceAtLot = (lot) => {
  if (!lot || !activePlacementItem.value) return false
  return (
    isInsideGrid(lot.x, lot.y, placementFootprint.value.width, placementFootprint.value.height) &&
    !isOccupied(lot.x, lot.y, placementFootprint.value.width, placementFootprint.value.height)
  )
}

const lotStyle = (lot) => {
  const point = toIso(lot.x, lot.y)
  return {
    left: `${point.left}px`,
    top: `${point.top}px`,
    width: `${gridConfig.tileWidth * 1.28}px`,
    height: `${gridConfig.tileHeight * 1.28}px`
  }
}

const placedItemStyle = (item) => {
  const anchorX = Number(item.position?.gridX || item.grid_x || 0)
  const anchorY = Number(item.position?.gridY || item.grid_y || 0)
  const width = Math.max(1, Number(item.footprint?.width || item.grid_width || 1))
  const height = Math.max(1, Number(item.footprint?.height || item.grid_height || 1))
  const point = toIso(anchorX + (width - 1) / 2, anchorY + (height - 1) / 2)
  return {
    left: `${point.left}px`,
    top: `${point.top}px`
  }
}

const previewSpriteStyle = computed(() => {
  if (!hoveredLot.value || !activePlacementItem.value) return null
  const point = toIso(
    hoveredLot.value.x + (placementFootprint.value.width - 1) / 2,
    hoveredLot.value.y + (placementFootprint.value.height - 1) / 2
  )
  return {
    left: `${point.left}px`,
    top: `${point.top}px`
  }
})

const previewValid = computed(() => canPlaceAtLot(hoveredLot.value))

const setHoverLot = (lot) => {
  hoveredLotKey.value = lot?.key || ''
}

const clearHoverLot = () => {
  hoveredLotKey.value = ''
  if (activePlacementItem.value) {
    inventoryStore.updateGhostPreview({ gridX: null, gridY: null, valid: false })
  }
}

const placeAtLot = async (lot) => {
  if (!activePlacementItem.value || !lot || isSubmitting.value) return
  setHoverLot(lot)
  if (!canPlaceAtLot(lot)) {
    feedback.value = isLotOccupied(lot) ? '这块地已经建好房子了，换一块地试试。' : '这栋建筑需要更大的空地。'
    return
  }

  isSubmitting.value = true
  feedback.value = ''
  try {
    const response = await unifiedShopApi.place(
      username.value,
      activePlacementItem.value.itemId,
      null,
      lot.x,
      0,
      lot.y,
      0,
      1,
      'isometric-city',
      '2D',
      lot.x,
      lot.y
    )
    const placedItem = inventoryStore.completePlacement(response.data?.placed_item, activePlacementItem.value)
    selectedPlacedId.value = placedItem.id
    recentlyPlacedIds.value.add(String(placedItem.id))
    setTimeout(() => recentlyPlacedIds.value.delete(String(placedItem.id)), 800)
    feedback.value = `${placedItem.nameCn || placedItem.name} 已建造完成。`
  } catch (error) {
    feedback.value = error.response?.data?.detail || '建造失败，请稍后再试。'
  } finally {
    isSubmitting.value = false
  }
}

const removeSelectedPlacedItem = async () => {
  if (!selectedPlacedItem.value) return
  const targetName = selectedPlacedItem.value.nameCn || selectedPlacedItem.value.name
  if (!window.confirm(`确认移除 ${targetName} 吗？`)) return

  try {
    await unifiedShopApi.removePlaced(selectedPlacedItem.value.id, username.value)
    inventoryStore.handlePlacedItemRemoval(selectedPlacedItem.value)
    await inventoryStore.refreshInventory(username.value)
    selectedPlacedId.value = ''
    feedback.value = '建筑已回收到背包。'
  } catch (error) {
    feedback.value = error.response?.data?.detail || '移除失败，请稍后再试。'
  }
}

const openShop = () => {
  dimensionStore.setDimension('GAIA')
  router.push('/shop')
}

const openBackpack = () => {
  window.dispatchEvent(new CustomEvent('blueprint-vault-open'))
}

watch([activePlacementItem, hoveredLot], () => {
  if (!activePlacementItem.value || !hoveredLot.value) return
  inventoryStore.updateGhostPreview({
    gridX: hoveredLot.value.x,
    gridY: hoveredLot.value.y,
    valid: previewValid.value
  })
})

watch(activePlacementItem, (nextItem) => {
  if (!nextItem) {
    feedback.value = ''
    return
  }
  feedback.value = `正在建造 ${nextItem.nameCn || nextItem.name}，请选择一块发光地基。`
})

onMounted(async () => {
  window.addEventListener('resize', onResize, { passive: true })
  isLoading.value = true
  await inventoryStore.refreshPlacedItems(username.value)
  isLoading.value = false
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  if (resizeRaf) cancelAnimationFrame(resizeRaf)
})
</script>

<template>
  <div class="gaia-builder-page">
    <div v-if="isLoading" class="stage-loading kenney-hud-panel">正在同步盖亚建筑...</div>

    <template v-else>
      <section class="gaia-build-hint" :class="{ active: activePlacementItem }">
        <span>{{ activePlacementItem ? '建造模式' : '盖亚拓扑' }}</span>
        <strong>{{ activePlacementItem ? '点击发光地块放置建筑' : '购买房子，然后从背包选择建筑开始建造' }}</strong>
        <button v-if="!activePlacementItem" type="button" @click="openShop">购买建筑</button>
      </section>

      <section v-if="!isLoading" class="city-stats">
        <div class="stat-item">
          <span class="stat-label">已建造</span>
          <strong class="stat-value">{{ occupiedLotCount }}</strong>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-label">空地块</span>
          <strong class="stat-value">{{ availableLotCount }}</strong>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-label">总地块</span>
          <strong class="stat-value">{{ buildLots.length }}</strong>
        </div>
      </section>

      <button v-if="!gaiaPlacedItems.length && !activePlacementItem" type="button" class="empty-build-card" @click="openShop">
        <span>还没有建筑</span>
        <strong>购买第一栋房子</strong>
        <small>盖亚拓扑会在这里显示你的 2D 建筑群。</small>
      </button>

      <div class="gaia-stage" @mouseleave="clearHoverLot">
        <div
          class="scene-surface"
          :style="{
            width: `${sceneWidth}px`,
            height: `${sceneHeight}px`,
            transform: `translate(-50%, -43%) scale(${sceneScale})`
          }"
        >
          <!-- Grid terrain underlay -->
          <svg
            class="grid-underlay"
            :width="sceneWidth"
            :height="sceneHeight"
            xmlns="http://www.w3.org/2000/svg"
          >
            <template v-for="gx in gridConfig.cols" :key="'gx-' + gx">
              <polygon
                v-for="gy in gridConfig.rows"
                :key="'gy-' + gx + '-' + gy"
                :points="tilePolygonPoints(gx - 1, gy - 1)"
                fill="none"
                :stroke="isBuildArea(gx - 1, gy - 1) ? 'rgba(61, 235, 167, 0.08)' : 'rgba(115, 224, 255, 0.04)'"
                stroke-width="0.5"
              />
            </template>
          </svg>
          <button
            v-for="lot in buildLots"
            :key="lot.key"
            type="button"
            class="build-lot"
            :class="{
              hovered: hoveredLotKey === lot.key,
              occupied: isLotOccupied(lot),
              available: activePlacementItem && canPlaceAtLot(lot),
              invalid: activePlacementItem && hoveredLotKey === lot.key && !canPlaceAtLot(lot),
              'selected-lot': selectedLotKey === lot.key
            }"
            :style="lotStyle(lot)"
            :aria-label="lot.label"
            @mouseenter="setHoverLot(lot)"
            @focus="setHoverLot(lot)"
            @click.stop="placeAtLot(lot)"
          >
            <span class="lot-glow" />
            <b>{{ isLotOccupied(lot) ? '已建造' : '可建造' }}</b>
          </button>

          <button
            v-if="activePlacementItem && previewSpriteStyle"
            type="button"
            class="placed-sprite ghost"
            :class="{ invalid: !previewValid }"
            :style="previewSpriteStyle"
            @click.stop="placeAtLot(hoveredLot)"
          >
            <img
              :src="activePlacementItem.previewPath || activePlacementItem.spritePath || activePlacementItem.assetPath"
              :alt="activePlacementItem.nameCn || activePlacementItem.name"
            >
            <span class="placed-label">{{ activePlacementItem.nameCn || activePlacementItem.name }}</span>
          </button>

          <button
            v-for="item in gaiaPlacedItems"
            :key="item.id"
            type="button"
            class="placed-sprite"
            :class="{
              selected: String(selectedPlacedId) === String(item.id),
              vehicle: item.subcategory === 'vehicles',
              'just-placed': recentlyPlacedIds.has(String(item.id))
            }"
            :style="placedItemStyle(item)"
            @click.stop="selectedPlacedId = String(item.id)"
          >
            <img :src="item.spritePath || item.previewPath || item.assetPath" :alt="item.nameCn || item.name">
            <span class="placed-label">{{ item.nameCn || item.name }}</span>
            <Transition name="info-pop">
              <div v-if="String(selectedPlacedId) === String(item.id)" class="building-info-popup">
                <strong>{{ item.nameCn || item.name }}</strong>
                <span class="popup-category">{{ item.category }}</span>
                <span class="popup-coords">[{{ item.position?.gridX ?? item.grid_x }}, {{ item.position?.gridY ?? item.grid_y }}]</span>
              </div>
            </Transition>
          </button>
        </div>
      </div>

      <p v-if="feedback" class="builder-feedback">{{ feedback }}</p>

      <div v-if="selectedPlacedItem" class="selected-bar kenney-hud-panel">
        <div>
          <span class="selected-kicker">已建建筑</span>
          <strong class="selected-name">{{ selectedPlacedItem.nameCn || selectedPlacedItem.name }}</strong>
          <small class="selected-meta">{{ selectedPlacedItem.category }} / [{{ selectedPlacedItem.position?.gridX ?? selectedPlacedItem.grid_x }}, {{ selectedPlacedItem.position?.gridY ?? selectedPlacedItem.grid_y }}]</small>
        </div>
        <button type="button" class="selected-btn" @click="openShop">去商店</button>
        <button type="button" class="selected-btn danger" @click="removeSelectedPlacedItem">移除</button>
      </div>

      <button type="button" class="backpack-quick" :class="{ building: activePlacementItem }" @click="openBackpack">打开背包建造</button>
    </template>
  </div>
</template>

<style scoped>
.gaia-builder-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: transparent;
}

.stage-loading {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  color: #eef7ff;
  font-size: 18px;
}

.gaia-stage {
  position: fixed;
  inset: 0;
  overflow: hidden;
  padding-top: 86px;
}

.scene-surface {
  position: absolute;
  left: 50%;
  top: 50%;
  transform-origin: center center;
  transition: transform 0.3s ease;
}

/* ── grid terrain underlay ── */
.grid-underlay {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
  opacity: 0.7;
}

/* ── shared HUD glass ── */
.gaia-build-hint,
.empty-build-card,
.builder-feedback,
.selected-bar,
.backpack-quick,
.city-stats {
  position: fixed;
  z-index: 8;
  border: 1px solid rgba(115, 224, 255, 0.18);
  background: rgba(8, 18, 38, 0.72);
  backdrop-filter: blur(18px);
  box-shadow: 0 20px 54px rgba(3, 8, 22, 0.34);
  color: #eef7ff;
}

.gaia-build-hint {
  left: 24px;
  top: 96px;
  width: min(360px, calc(100vw - 48px));
  border-radius: 24px;
  padding: 16px 18px;
  display: grid;
  gap: 8px;
}

.gaia-build-hint span,
.selected-kicker,
.stat-label {
  color: rgba(156, 230, 255, 0.78);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.gaia-build-hint strong {
  font-size: 15px;
  line-height: 1.35;
}

.gaia-build-hint button,
.empty-build-card,
.selected-btn,
.backpack-quick {
  border: 0;
  cursor: pointer;
}

.gaia-build-hint button {
  justify-self: start;
  height: 36px;
  border-radius: 12px;
  padding: 0 14px;
  background: #4880ff;
  color: white;
  font-weight: 800;
}

/* ── city stats HUD ── */
.city-stats {
  right: 24px;
  top: 96px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-radius: 18px;
  padding: 10px 20px;
}

.stat-item {
  display: grid;
  gap: 2px;
  text-align: center;
}

.stat-value {
  font-size: 22px;
  line-height: 1;
}

.stat-divider {
  width: 1px;
  height: 28px;
  background: rgba(115, 224, 255, 0.2);
}

.empty-build-card {
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: min(340px, calc(100vw - 44px));
  border-radius: 28px;
  padding: 24px;
  display: grid;
  gap: 8px;
  text-align: center;
}

.empty-build-card span,
.empty-build-card small {
  color: rgba(238, 247, 255, 0.68);
}

.empty-build-card strong {
  font-size: 22px;
}

/* ── build lots ── */
.build-lot,
.placed-sprite {
  position: absolute;
  transform: translate(-50%, -50%);
}

.build-lot {
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
  color: rgba(238, 247, 255, 0.72);
  transition: transform 0.18s ease;
}

.build-lot:hover {
  transform: translate(-50%, -50%) scale(1.05);
  z-index: 3;
}

.build-lot::before {
  content: '';
  position: absolute;
  inset: 6px;
  clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
  background:
    linear-gradient(180deg, rgba(74, 118, 76, 0.9), rgba(28, 64, 48, 0.9)),
    #315f44;
  border: 1px solid rgba(173, 255, 205, 0.18);
  box-shadow: 0 20px 28px rgba(0, 0, 0, 0.22);
  transition: background 0.28s ease, border-color 0.28s ease, box-shadow 0.28s ease, opacity 0.28s ease, filter 0.28s ease;
}

/* available: pulsing green glow */
@keyframes lotPulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(61, 235, 167, 0.16), 0 0 38px rgba(61, 235, 167, 0.26); }
  50% { box-shadow: 0 0 0 4px rgba(61, 235, 167, 0.28), 0 0 52px rgba(61, 235, 167, 0.38); }
}

.build-lot.available::before {
  background:
    linear-gradient(180deg, rgba(71, 184, 132, 0.95), rgba(34, 116, 86, 0.96)),
    #2f8f65;
  border-color: rgba(126, 255, 195, 0.68);
  animation: lotPulse 2s ease-in-out infinite;
}

.build-lot.hovered::before {
  background: linear-gradient(180deg, rgba(100, 210, 160, 0.98), rgba(48, 140, 100, 0.98));
  border-color: rgba(160, 255, 220, 0.85);
  box-shadow: 0 0 0 3px rgba(61, 235, 167, 0.3), 0 0 48px rgba(61, 235, 167, 0.4);
}

.build-lot.occupied::before {
  opacity: 0.35;
  filter: grayscale(0.3);
}

/* invalid: shake */
@keyframes lotShake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-3px); }
  40% { transform: translateX(3px); }
  60% { transform: translateX(-2px); }
  80% { transform: translateX(2px); }
}

.build-lot.invalid::before {
  background: linear-gradient(180deg, rgba(197, 69, 91, 0.82), rgba(111, 33, 54, 0.9));
  border-color: rgba(255, 143, 163, 0.5);
  box-shadow: 0 0 28px rgba(255, 95, 109, 0.22);
  animation: lotShake 0.4s ease-in-out;
}

/* selected lot: blue glow under the selected building */
.build-lot.selected-lot::before {
  background: linear-gradient(180deg, rgba(86, 173, 255, 0.6), rgba(40, 100, 200, 0.7));
  border-color: rgba(86, 173, 255, 0.6);
  box-shadow: 0 0 28px rgba(86, 173, 255, 0.35);
}

.lot-glow {
  position: absolute;
  inset: 16px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(173, 255, 205, 0.2), transparent 68%);
}

/* glow pulse for available lots */
@keyframes glowPulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.15); }
}

.build-lot.available .lot-glow {
  animation: glowPulse 2s ease-in-out infinite;
}

.build-lot b {
  position: absolute;
  left: 50%;
  top: calc(50% + 32px);
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: 11px;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.build-lot:hover b,
.build-lot.available b,
.build-lot.invalid b,
.build-lot.selected-lot b {
  opacity: 1;
}

/* ── placed building sprites ── */
.placed-sprite {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
  transform: translate(-50%, calc(-100% + 18px));
  transition: transform 0.2s ease, filter 0.2s ease;
}

.placed-sprite:hover {
  transform: translate(-50%, calc(-100% + 14px));
  z-index: 5;
}

.placed-sprite:active {
  transform: translate(-50%, calc(-100% + 20px)) scale(0.97);
}

.placed-sprite img {
  width: 122px;
  image-rendering: pixelated;
  filter: saturate(1.08) brightness(1.04) drop-shadow(0 16px 24px rgba(3, 8, 22, 0.42));
}

.placed-sprite.vehicle img {
  width: 76px;
}

/* ghost preview: gentle bob */
@keyframes ghostBob {
  0%, 100% { transform: translate(-50%, calc(-100% + 18px)); }
  50% { transform: translate(-50%, calc(-100% + 14px)); }
}

.placed-sprite.ghost {
  opacity: 0.76;
  pointer-events: auto;
  animation: ghostBob 1.2s ease-in-out infinite;
}

.placed-sprite.ghost.invalid img {
  filter: saturate(0.7) brightness(0.92) hue-rotate(-30deg) drop-shadow(0 0 18px rgba(255, 114, 141, 0.3));
}

/* selected: enhanced double-glow */
.placed-sprite.selected img {
  filter: saturate(1.2) brightness(1.1)
    drop-shadow(0 0 12px rgba(86, 173, 255, 0.8))
    drop-shadow(0 0 28px rgba(86, 173, 255, 0.4));
}

.placed-sprite.selected .placed-label {
  background: rgba(72, 128, 255, 0.35);
  border-color: rgba(86, 173, 255, 0.6);
}

/* selection ring beneath building */
@keyframes selectionPulse {
  0%, 100% { box-shadow: 0 0 8px rgba(86, 173, 255, 0.3); transform: translateX(-50%) scale(1); }
  50% { box-shadow: 0 0 20px rgba(86, 173, 255, 0.5); transform: translateX(-50%) scale(1.1); }
}

.placed-sprite.selected::before {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 90px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid rgba(86, 173, 255, 0.5);
  animation: selectionPulse 1.8s ease-in-out infinite;
}

/* ── building drop animation ── */
@keyframes buildingDrop {
  0% {
    transform: translate(-50%, calc(-100% + 18px - 80px)) scale(0.8);
    opacity: 0;
    filter: brightness(2);
  }
  40% {
    opacity: 1;
    filter: brightness(1.3);
  }
  65% {
    transform: translate(-50%, calc(-100% + 18px + 6px)) scale(1.04);
    filter: brightness(1);
  }
  85% {
    transform: translate(-50%, calc(-100% + 18px - 2px)) scale(0.98);
  }
  100% {
    transform: translate(-50%, calc(-100% + 18px)) scale(1);
    filter: brightness(1);
  }
}

.placed-sprite.just-placed {
  animation: buildingDrop 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes dustBurst {
  0% { transform: translateX(-50%) scale(0.3); opacity: 1; }
  100% { transform: translateX(-50%) scale(2); opacity: 0; }
}

.placed-sprite.just-placed::after {
  content: '';
  position: absolute;
  bottom: -12px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 20px;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(255, 255, 255, 0.25), transparent 70%);
  animation: dustBurst 0.5s ease-out forwards;
}

.placed-label {
  display: block;
  margin-top: 7px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(7, 16, 34, 0.86);
  color: #dff4ff;
  font-size: 11px;
  white-space: nowrap;
  border: 1px solid rgba(115, 224, 255, 0.2);
}

/* ── info popup ── */
.building-info-popup {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  padding: 8px 14px;
  border-radius: 14px;
  background: rgba(8, 18, 38, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(86, 173, 255, 0.4);
  box-shadow: 0 8px 28px rgba(3, 8, 22, 0.5);
  color: #eef7ff;
  font-size: 12px;
  display: grid;
  gap: 2px;
  text-align: center;
  z-index: 10;
}

.popup-category {
  color: rgba(156, 230, 255, 0.7);
  font-size: 10px;
}

.popup-coords {
  color: rgba(156, 230, 255, 0.5);
  font-size: 10px;
  font-family: monospace;
}

.info-pop-enter-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); }
.info-pop-leave-active { transition: all 0.15s ease; }
.info-pop-enter-from { opacity: 0; transform: translateX(-50%) translateY(8px) scale(0.9); }
.info-pop-leave-to { opacity: 0; transform: translateX(-50%) translateY(-4px) scale(0.95); }

/* ── feedback & bars ── */
.builder-feedback {
  left: 50%;
  bottom: 104px;
  transform: translateX(-50%);
  max-width: calc(100vw - 44px);
  margin: 0;
  border-radius: 999px;
  padding: 10px 16px;
  color: #dff4ff;
  font-size: 13px;
  animation: feedbackSlideIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes feedbackSlideIn {
  from { transform: translateX(-50%) translateY(12px); opacity: 0; }
  to { transform: translateX(-50%) translateY(0); opacity: 1; }
}

.selected-bar {
  left: 50%;
  bottom: 28px;
  transform: translateX(-50%);
  min-width: 310px;
  max-width: calc(100vw - 44px);
  border-radius: 22px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  animation: barSlideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes barSlideUp {
  from { transform: translateX(-50%) translateY(20px); opacity: 0; }
  to { transform: translateX(-50%) translateY(0); opacity: 1; }
}

.selected-bar > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.selected-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-meta {
  color: rgba(156, 230, 255, 0.6);
  font-size: 11px;
}

.selected-btn {
  min-height: 36px;
  border-radius: 12px;
  padding: 0 13px;
  background: rgba(255, 255, 255, 0.1);
  color: #eef7ff;
  font-weight: 800;
}

.selected-btn.danger {
  background: rgba(255, 101, 133, 0.18);
  color: #ffd6df;
}

/* ── backpack button ── */
.backpack-quick {
  right: 22px;
  bottom: 84px;
  min-height: 42px;
  border-radius: 16px;
  padding: 0 16px;
  background: rgba(72, 128, 255, 0.9);
  color: white;
  font-weight: 900;
}

@keyframes subtlePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(72, 128, 255, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(72, 128, 255, 0); }
}

.backpack-quick.building {
  animation: subtlePulse 2.5s ease-in-out infinite;
}

/* ── responsive ── */
@media (max-width: 768px) {
  .gaia-build-hint {
    left: 12px;
    top: 82px;
  }

  .city-stats {
    right: 12px;
    top: 82px;
    gap: 10px;
    padding: 8px 14px;
  }

  .stat-value {
    font-size: 18px;
  }

  .gaia-stage {
    padding-top: 72px;
  }

  .selected-bar {
    bottom: 112px;
    flex-wrap: wrap;
  }

  .backpack-quick {
    right: 12px;
    bottom: 66px;
  }
}
</style>
