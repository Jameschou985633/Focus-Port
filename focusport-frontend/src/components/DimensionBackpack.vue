<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const router = useRouter()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()

const isOpen = ref(false)

const groupedInventory = computed(() => ([
  {
    code: 'PHYSICAL',
    label: composeWorldLabel(WORLD_NAMES.physical),
    items: inventoryStore.inventoryByDimension.PHYSICAL || []
  },
  {
    code: 'GAIA',
    label: composeWorldLabel(WORLD_NAMES.gaia),
    items: inventoryStore.inventoryByDimension.GAIA || []
  }
]))

const totalItems = computed(() => groupedInventory.value.reduce((sum, section) => sum + section.items.length, 0))

const isDraftItem = (item) => (
  inventoryStore.placementDraft?.inventoryId === item.inventoryId
)

const canPlaceItem = (item) => {
  if (item.dimension === 'GAIA') {
    return ['building', 'vehicle'].includes(item.placementType)
  }
  return ['building', 'greenery'].includes(item.placementType)
}

const handlePlaceItem = (item) => {
  if (!canPlaceItem(item)) return
  if (isDraftItem(item)) {
    inventoryStore.cancelPlacement()
    return
  }
  isOpen.value = true
  dimensionStore.setDimension(item.dimension)
  inventoryStore.beginPlacement(item)
}

const openShop = () => router.push('/shop')

const handleOpenVault = () => {
  isOpen.value = true
}

onMounted(() => {
  window.addEventListener('blueprint-vault-open', handleOpenVault)
})

onUnmounted(() => {
  window.removeEventListener('blueprint-vault-open', handleOpenVault)
})
</script>

<template>
  <section class="backpack-shell" :class="{ open: isOpen }">
    <button type="button" class="backpack-toggle" data-blueprint-vault-anchor @click="isOpen = !isOpen">
      <span>{{ composeWorldLabel(WORLD_NAMES.blueprintVault) }}</span>
      <strong>{{ totalItems }}</strong>
    </button>

    <div v-if="isOpen" class="backpack-panel">
      <header class="panel-header">
        <div>
          <span class="panel-eyebrow">{{ WORLD_NAMES.blueprintVault.en }}</span>
          <strong>{{ composeWorldLabel(WORLD_NAMES.blueprintVault) }}</strong>
        </div>
        <button type="button" class="shop-link" @click="openShop">{{ composeWorldLabel(WORLD_NAMES.exchangePort) }}</button>
      </header>

      <p v-if="inventoryStore.isPlacing" class="placement-hint">
        正在准备部署 {{ inventoryStore.placementDraft?.nameCn || inventoryStore.placementDraft?.name }}
      </p>

      <div class="dimension-section-list">
        <section
          v-for="section in groupedInventory"
          :key="section.code"
          class="dimension-section"
          :class="{ active: dimensionStore.activeDimension === section.code }"
        >
          <header class="dimension-header">
            <strong>{{ section.label }}</strong>
            <span>{{ section.items.length }}</span>
          </header>

          <div v-if="section.items.length" class="item-list">
            <article
              v-for="item in section.items"
              :key="item.inventoryId"
              class="item-card"
              :class="{ active: isDraftItem(item) }"
            >
              <div class="thumb" :class="{ hologram: item.dimension === 'GAIA' }">
                <img
                  v-if="item.previewPath || item.spritePath"
                  :src="item.previewPath || item.spritePath"
                  :alt="item.nameCn || item.name"
                />
                <span v-else>{{ item.dimension === 'GAIA' ? 'GAIA' : '3D' }}</span>
              </div>

              <div class="item-copy">
                <strong>{{ item.nameCn || item.name }}</strong>
                <span>{{ item.dimension === 'GAIA' ? `占地 ${item.gridWidth}x${item.gridHeight}` : 'ENGINEERING DOCK 3D 实体' }}</span>
              </div>

              <button
                type="button"
                class="item-action"
                :class="{ active: isDraftItem(item), disabled: !canPlaceItem(item) }"
                :disabled="!canPlaceItem(item)"
                @click="handlePlaceItem(item)"
              >
                {{ !canPlaceItem(item) ? '不可放置' : isDraftItem(item) ? '取消' : '放置' }}
              </button>
            </article>
          </div>

          <div v-else class="empty-state">
            当前分舱还没有资产。
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<style scoped>
.backpack-shell {
  position: fixed;
  right: 22px;
  bottom: 20px;
  z-index: 32;
  width: min(340px, calc(100vw - 44px));
}

.backpack-toggle,
.shop-link,
.item-action {
  border: none;
  cursor: pointer;
}

.backpack-toggle {
  width: 100%;
  min-height: 48px;
  border-radius: 18px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background:
    linear-gradient(180deg, rgba(14, 28, 58, 0.96), rgba(6, 12, 26, 0.96)),
    #0a192f;
  color: #eef7ff;
  border: 1px solid rgba(115, 224, 255, 0.18);
  box-shadow: 0 18px 44px rgba(3, 8, 22, 0.4);
}

.backpack-toggle span,
.panel-eyebrow,
.dimension-header strong {
  text-shadow: 0 0 14px rgba(0, 255, 255, 0.14);
}

.backpack-toggle strong {
  min-width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(47, 216, 255, 0.18);
}

.backpack-panel {
  margin-top: 10px;
  border-radius: 22px;
  padding: 16px;
  background:
    radial-gradient(circle at top, rgba(47, 216, 255, 0.1), transparent 36%),
    linear-gradient(180deg, rgba(12, 27, 59, 0.96), rgba(7, 14, 32, 0.96));
  border: 1px solid rgba(115, 224, 255, 0.16);
  box-shadow: 0 24px 48px rgba(3, 8, 22, 0.38);
  color: #eef7ff;
  backdrop-filter: blur(14px);
}

.panel-header,
.dimension-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-eyebrow {
  display: block;
  margin-bottom: 4px;
  font-family: 'Roboto Mono', 'Consolas', monospace;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: rgba(156, 230, 255, 0.82);
}

.panel-header strong {
  font-size: 15px;
}

.shop-link {
  min-height: 36px;
  border-radius: 12px;
  padding: 0 12px;
  color: #eef7ff;
  background: rgba(255, 255, 255, 0.08);
}

.placement-hint {
  margin: 14px 0 0;
  color: #9ce6ff;
  font-size: 13px;
}

.dimension-section-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 14px;
  max-height: 380px;
  overflow: auto;
}

.dimension-section {
  border-radius: 18px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(115, 224, 255, 0.1);
}

.dimension-section.active {
  border-color: rgba(47, 216, 255, 0.34);
  box-shadow: inset 0 0 0 1px rgba(47, 216, 255, 0.12);
}

.dimension-header span {
  min-width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
}

.item-card {
  display: grid;
  grid-template-columns: 62px 1fr auto;
  align-items: center;
  gap: 12px;
  border-radius: 16px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.04);
}

.item-card.active {
  box-shadow: inset 0 0 0 1px rgba(47, 216, 255, 0.4);
  background: rgba(47, 216, 255, 0.08);
}

.thumb {
  width: 62px;
  height: 62px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: rgba(5, 11, 24, 0.72);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.thumb.hologram img {
  image-rendering: pixelated;
  mix-blend-mode: screen;
  filter: hue-rotate(178deg) saturate(1.3) brightness(1.2) drop-shadow(0 0 12px rgba(88, 228, 255, 0.4));
}

.item-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-copy strong {
  font-size: 14px;
}

.item-copy span {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.72);
}

.item-action {
  min-width: 74px;
  min-height: 38px;
  border-radius: 12px;
  color: #eef7ff;
  background: linear-gradient(180deg, #2fd8ff, #2d74ff);
}

.item-action.active {
  background: rgba(255, 255, 255, 0.08);
}

.item-action.disabled {
  cursor: not-allowed;
  opacity: 0.5;
  background: rgba(255, 255, 255, 0.12);
}

.empty-state {
  margin-top: 10px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  text-align: center;
  color: rgba(222, 240, 255, 0.76);
}

@media (max-width: 768px) {
  .backpack-shell {
    right: 12px;
    bottom: 88px;
    width: auto;
    max-width: calc(100vw - 24px);
  }
}
</style>
