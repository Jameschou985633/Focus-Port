<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'
import SpaceButton from './base/SpaceButton.vue'

const router = useRouter()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()

const username = ref(localStorage.getItem('username') || 'guest')
const activeTab = ref('PHYSICAL')

const groupedInventory = computed(() => ([
  {
    code: 'PHYSICAL',
    label: composeWorldLabel(WORLD_NAMES.physical),
    icon: '🏗️',
    items: inventoryStore.inventoryByDimension.PHYSICAL || []
  },
  {
    code: 'GAIA',
    label: composeWorldLabel(WORLD_NAMES.gaia),
    icon: '🌐',
    items: inventoryStore.inventoryByDimension.GAIA || []
  }
]))

const currentSection = computed(() => groupedInventory.value.find(s => s.code === activeTab.value))

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
  dimensionStore.setDimension(item.dimension)
  inventoryStore.beginPlacement(item)
  router.push('/')
}

const goBack = () => router.push('/')
const openShop = () => router.push('/shop')

onMounted(async () => {
  await inventoryStore.refreshInventory(username.value)
})
</script>

<template>
  <div class="vault-page space-theme">
    <div class="stars-bg"></div>

    <header class="page-header">
      <SpaceButton variant="secondary" size="sm" @click="goBack">← 返回</SpaceButton>
      <div class="title-wrap">
        <span class="title-icon">📦</span>
        <div>
          <p class="page-kicker">{{ WORLD_NAMES.blueprintVault.en }}</p>
          <h1>{{ composeWorldLabel(WORLD_NAMES.blueprintVault) }}</h1>
        </div>
      </div>
      <div class="header-stats">
        <span class="stat-badge">共 {{ totalItems }} 件资产</span>
      </div>
    </header>

    <div class="tab-bar">
      <button
        v-for="section in groupedInventory"
        :key="section.code"
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === section.code }"
        @click="activeTab = section.code"
      >
        <span class="tab-icon">{{ section.icon }}</span>
        <span class="tab-label">{{ section.label }}</span>
        <span class="tab-count">{{ section.items.length }}</span>
      </button>
    </div>

    <main class="vault-content">
      <div v-if="currentSection?.items.length" class="item-grid">
        <article
          v-for="item in currentSection.items"
          :key="item.inventoryId"
          class="item-card"
          :class="{ active: isDraftItem(item) }"
        >
          <div class="item-thumb" :class="{ hologram: item.dimension === 'GAIA' }">
            <img
              v-if="item.previewPath || item.spritePath"
              :src="item.previewPath || item.spritePath"
              :alt="item.nameCn || item.name"
            />
            <span v-else class="thumb-placeholder">{{ item.dimension === 'GAIA' ? 'GAIA' : '3D' }}</span>
          </div>

          <div class="item-info">
            <h3 class="item-name">{{ item.nameCn || item.name }}</h3>
            <p class="item-meta">
              <span v-if="item.dimension === 'GAIA'">占地 {{ item.gridWidth }}x{{ item.gridHeight }}</span>
              <span v-else>ENGINEERING DOCK 3D 实体</span>
            </p>
            <span class="item-type">{{ item.placementType || item.category }}</span>
          </div>

          <div class="item-actions">
            <button
              v-if="canPlaceItem(item)"
              type="button"
              class="place-btn"
              :class="{ cancelling: isDraftItem(item) }"
              @click="handlePlaceItem(item)"
            >
              {{ isDraftItem(item) ? '取消部署' : '前往放置' }}
            </button>
            <span v-else class="cannot-place">暂不支持放置</span>
          </div>
        </article>
      </div>

      <div v-else class="empty-state">
        <div class="empty-icon">📭</div>
        <h3>当前分舱还没有资产</h3>
        <p>前往物质交换港获取建筑与装饰</p>
        <SpaceButton variant="primary" @click="openShop">前往物质交换港</SpaceButton>
      </div>

      <div v-if="inventoryStore.isPlacing" class="placement-notice">
        <span class="notice-icon">📍</span>
        <span>正在准备部署 {{ inventoryStore.placementDraft?.nameCn || inventoryStore.placementDraft?.name }}</span>
      </div>
    </main>
  </div>
</template>

<style scoped>
.vault-page.space-theme {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #0a0f1a 100%);
  padding: 20px;
  color: white;
  font-family: 'Segoe UI', sans-serif;
  position: relative;
}

.stars-bg {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    radial-gradient(2px 2px at 20px 30px, #fff, transparent),
    radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
    radial-gradient(1px 1px at 90px 40px, #fff, transparent),
    radial-gradient(2px 2px at 160px 120px, rgba(255,255,255,0.6), transparent),
    radial-gradient(1px 1px at 230px 80px, #fff, transparent);
  background-size: 350px 200px;
  animation: twinkle 8s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
}

.title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.title-icon {
  font-size: 32px;
}

.page-kicker {
  margin: 0;
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(156, 223, 255, 0.7);
}

.page-header h1 {
  margin: 0;
  font-size: 1.4em;
  font-weight: 700;
  color: #3b82f6;
  text-shadow: 0 0 18px rgba(0, 255, 255, 0.2);
}

.header-stats {
  display: flex;
  gap: 8px;
}

.stat-badge {
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.85em;
  font-weight: 600;
}

.tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 12px;
  color: rgba(222, 240, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(115, 224, 255, 0.3);
}

.tab-btn.active {
  background: linear-gradient(180deg, rgba(49, 120, 255, 0.25), rgba(18, 35, 78, 0.9));
  border-color: rgba(115, 224, 255, 0.4);
  color: #eef7ff;
  box-shadow: 0 0 20px rgba(49, 120, 255, 0.2);
}

.tab-icon {
  font-size: 18px;
}

.tab-label {
  font-weight: 600;
}

.tab-count {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.8em;
}

.vault-content {
  position: relative;
  z-index: 1;
}

.item-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.item-card {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s;
}

.item-card:hover {
  border-color: rgba(115, 224, 255, 0.35);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.item-card.active {
  border-color: #3b82f6;
  box-shadow: 0 0 24px rgba(59, 130, 246, 0.3);
}

.item-thumb {
  width: 100%;
  height: 120px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.item-thumb.hologram {
  background: linear-gradient(135deg, rgba(109, 92, 255, 0.15), rgba(76, 222, 255, 0.1));
  border: 1px solid rgba(109, 92, 255, 0.3);
}

.item-thumb img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.thumb-placeholder {
  font-size: 24px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 0.1em;
}

.item-info {
  flex: 1;
}

.item-name {
  margin: 0 0 4px;
  font-size: 1em;
  font-weight: 700;
  color: #eef7ff;
}

.item-meta {
  margin: 0 0 6px;
  font-size: 0.85em;
  color: rgba(222, 240, 255, 0.6);
}

.item-type {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(59, 130, 246, 0.15);
  border-radius: 4px;
  font-size: 0.75em;
  color: rgba(156, 223, 255, 0.8);
}

.item-actions {
  display: flex;
  justify-content: flex-end;
}

.place-btn {
  padding: 8px 16px;
  background: linear-gradient(180deg, #2fd8ff, #2d74ff);
  border: none;
  border-radius: 10px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.place-btn:hover {
  box-shadow: 0 4px 16px rgba(47, 216, 255, 0.3);
}

.place-btn.cancelling {
  background: linear-gradient(180deg, #ff6b6b, #ee5a5a);
}

.cannot-place {
  font-size: 0.85em;
  color: rgba(222, 240, 255, 0.5);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #eef7ff;
}

.empty-state p {
  margin: 0 0 20px;
  color: rgba(222, 240, 255, 0.6);
}

.placement-notice {
  position: fixed;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(180deg, rgba(16, 34, 74, 0.95), rgba(8, 16, 36, 0.95));
  border: 1px solid rgba(115, 224, 255, 0.3);
  border-radius: 999px;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #eef7ff;
  font-size: 0.9em;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.notice-icon {
  font-size: 18px;
}

@media (max-width: 768px) {
  .page-header {
    flex-wrap: wrap;
  }

  .tab-bar {
    overflow-x: auto;
    padding-bottom: 8px;
  }

  .tab-label {
    display: none;
  }

  .item-grid {
    grid-template-columns: 1fr;
  }
}
</style>
