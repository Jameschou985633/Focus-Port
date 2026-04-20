<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { unifiedShopApi } from '../../api'
import NavRail from '../NavRail.vue'
import { useDimensionStore } from '../../stores/dimension'
import { useInventoryStore } from '../../stores/inventory'
import {
  GAIA_SIMULATOR_ASSETS,
  GAIA_SIMULATOR_ASSET_MAP,
  PHYSICAL_BAY_ASSET_MAP
} from '../../constants/assets'
import { WORLD_NAMES, composeWorldLabel } from '../../constants/worldNames'
import '../../assets/kenney-ui/kenney-hud.css'

const router = useRouter()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()
const username = ref(localStorage.getItem('username') || 'guest')

const activeFacet = ref('all')
const gradeFilter = ref('all')
const sortBy = ref('grade_desc')
const searchQuery = ref('')
const backendItems = ref([])
const isLoading = ref(false)
const purchasingId = ref(null)
const userSunshine = ref(0)
const userCoins = ref(0)
const previewItem = ref(null)
const feedbackMessage = ref('')

const gradeOrder = { legendary: 5, epic: 4, rare: 3, common: 2, c: 1, b: 2, a: 3, s: 4 }
const isImagePath = (value) => /\.(png|jpe?g|webp|gif|svg)$/i.test(String(value || ''))

const currentDimension = computed(() => dimensionStore.activeDimension)

const dimensionTabs = [
  { code: 'PHYSICAL', label: composeWorldLabel(WORLD_NAMES.physical), caption: '3D 实体模型与槽位部署' },
  { code: 'GAIA', label: composeWorldLabel(WORLD_NAMES.gaia), caption: '2D 等距资产' }
]

const categoryTabs = computed(() => (
  currentDimension.value === 'GAIA'
    ? [
        { code: 'all', label: '全部' },
        { code: 'buildings', label: '建筑' },
        { code: 'vehicles', label: '车辆' }
      ]
    : [
        { code: 'all', label: '全部' },
        { code: 'building', label: '建筑' },
        { code: 'greenery', label: '绿化' }
      ]
))

const mergedItems = computed(() => {
  const backendByItemCode = new Map()
  const backendByAssetPath = new Map()

  for (const item of backendItems.value) {
    if (item.item_code) backendByItemCode.set(item.item_code, item)
    if (item.model_path) backendByAssetPath.set(item.model_path, item)
    if (item.preview_path) backendByAssetPath.set(item.preview_path, item)
    if (item.sprite_path) backendByAssetPath.set(item.sprite_path, item)
  }

  if (currentDimension.value === 'GAIA') {
    const sourceItems = backendItems.value.length ? backendItems.value : GAIA_SIMULATOR_ASSETS
    return sourceItems.map((entry) => {
      const catalogEntry = GAIA_SIMULATOR_ASSET_MAP.get(entry.item_code) || GAIA_SIMULATOR_ASSET_MAP.get(entry.assetPath) || entry
      const backendEntry = backendItems.value.length
        ? entry
        : backendByItemCode.get(entry.itemCode) || backendByAssetPath.get(entry.assetPath)

      return {
        id: backendEntry?.id ?? null,
        item_code: backendEntry?.item_code || entry.itemCode || entry.assetId,
        name: backendEntry?.name || entry.name,
        name_cn: backendEntry?.name_cn || entry.nameCn || entry.name,
        preview_path: backendEntry?.preview_path || entry.previewPath || entry.assetPath,
        sprite_path: backendEntry?.sprite_path || entry.spritePath || entry.assetPath,
        model_path: backendEntry?.model_path || '',
        category: backendEntry?.category || entry.category || 'structures',
        subcategory: backendEntry?.subcategory || entry.subcategory || 'buildings',
        placement_type: backendEntry?.placement_type || (entry.subcategory === 'vehicles' ? 'vehicle' : 'building'),
        grid_width: backendEntry?.grid_width || entry.footprint?.width || 1,
        grid_height: backendEntry?.grid_height || entry.footprint?.height || 1,
        rarity: backendEntry?.rarity || entry.rarity || 'common',
        grade: backendEntry?.grade || backendEntry?.rarity || entry.rarity || 'common',
        available_to_place_count: backendEntry?.available_to_place_count || 0,
        placed_count: backendEntry?.placed_count || 0,
        owned_count: backendEntry?.owned_count || 0,
        slot_capacity_remaining: backendEntry?.slot_capacity_remaining || 0,
        price_coins: backendEntry?.price_coins ?? entry.priceCoins ?? 0,
        price_sunshine: backendEntry?.price_sunshine ?? entry.priceSunshine ?? 0,
        description: backendEntry?.description || 'GAIA 模拟资产',
        dimension: 'GAIA',
        sync_pending: !backendEntry?.id
      }
    })
  }

  return backendItems.value.map((entry) => {
    const catalogEntry =
      PHYSICAL_BAY_ASSET_MAP.get(entry.model_path) ||
      PHYSICAL_BAY_ASSET_MAP.get(entry.preview_path) ||
      PHYSICAL_BAY_ASSET_MAP.get(entry.item_code) ||
      null

    return {
      ...entry,
      preview_path: [entry.preview_path, entry.sprite_path, catalogEntry?.previewPath, catalogEntry?.assetPath].find((path) => isImagePath(path)) || '',
      sprite_path: entry.sprite_path || catalogEntry?.spritePath || '',
      model_path: entry.model_path || catalogEntry?.assetPath || '',
      rarity: entry.rarity || catalogEntry?.rarity || 'common',
      grade: entry.grade || entry.rarity || catalogEntry?.rarity || 'common',
      description: entry.description || 'PHYSICAL 实体建造资产',
      dimension: 'PHYSICAL',
      sync_pending: false
    }
  })
})

const getItemFacet = (item) => {
  if (currentDimension.value === 'GAIA') {
    return item.subcategory === 'vehicles' ? 'vehicles' : 'buildings'
  }
  return item.placement_type || 'building'
}

const filteredItems = computed(() => {
  let result = [...mergedItems.value]

  if (activeFacet.value !== 'all') {
    result = result.filter((item) => getItemFacet(item) === activeFacet.value)
  }

  if (gradeFilter.value !== 'all') {
    result = result.filter((item) => String(item.grade || item.rarity || '').toLowerCase() === gradeFilter.value.toLowerCase())
  }

  if (searchQuery.value.trim()) {
    const query = searchQuery.value.trim().toLowerCase()
    result = result.filter((item) =>
      [item.name, item.name_cn, item.item_code].some((field) => String(field || '').toLowerCase().includes(query))
    )
  }

  if (sortBy.value === 'price_asc') {
    result.sort((a, b) => getItemPrice(a).amount - getItemPrice(b).amount)
  } else if (sortBy.value === 'price_desc') {
    result.sort((a, b) => getItemPrice(b).amount - getItemPrice(a).amount)
  } else if (sortBy.value === 'name') {
    result.sort((a, b) => String(a.name_cn || a.name || '').localeCompare(String(b.name_cn || b.name || '')))
  } else {
    result.sort((a, b) => (gradeOrder[String(b.grade || '').toLowerCase()] || 0) - (gradeOrder[String(a.grade || '').toLowerCase()] || 0))
  }

  return result
})

const loadBalance = async () => {
  try {
    const response = await unifiedShopApi.balance(username.value)
    userSunshine.value = response.data.diamonds || response.data.sunshine || 0
    userCoins.value = response.data.coins || 0
  } catch (error) {
    console.error('Failed to load balance', error)
  }
}

const loadItems = async () => {
  isLoading.value = true
  try {
    const response = await unifiedShopApi.items({
      username: username.value,
      dimension: inventoryStore.toBackendDimension(currentDimension.value)
    })
    backendItems.value = response.data.items || []
    if (!backendItems.value.length && currentDimension.value === 'GAIA') {
      feedbackMessage.value = 'GAIA 资产正在与后端目录同步，请稍后刷新。'
    }
  } catch (error) {
    console.error('Failed to load shop items', error)
    backendItems.value = []
    feedbackMessage.value = '物质交换港目录载入失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

const reloadShopState = async () => {
  await Promise.all([
    loadBalance(),
    loadItems(),
    inventoryStore.refreshInventory(username.value)
  ])
}

const getItemPrice = (item) => {
  if (Number(item.price_coins || 0) > 0) {
    return { amount: Number(item.price_coins || 0), currency: 'coins', icon: WORLD_NAMES.currency.en, label: WORLD_NAMES.currency.zh }
  }
  return { amount: Number(item.price_sunshine || 0), currency: 'diamonds', icon: 'ENERGY', label: '专注能量' }
}

const isPurchasing = (item) => (
  purchasingId.value !== null &&
  item?.id !== null &&
  item?.id !== undefined &&
  purchasingId.value === item.id
)

const canAfford = (item) => {
  const price = getItemPrice(item)
  return price.currency === 'coins' ? userCoins.value >= price.amount : userSunshine.value >= price.amount
}

const getPrimaryAction = (item) => {
  if (item.sync_pending || !item.id) {
    return { label: '等待同步', disabled: true, mode: 'pending' }
  }

  if ((item.available_to_place_count || 0) > 0) {
    if (currentDimension.value === 'PHYSICAL' && Number(item.slot_capacity_remaining || 0) <= 0) {
      return { label: item.placement_type === 'greenery' ? '绿化位已满' : '建筑位已满', disabled: true, mode: 'full' }
    }
    return { label: '背包放置', disabled: false, mode: 'place' }
  }

  const affordable = canAfford(item)
  return { label: affordable ? '购买' : '余额不足', disabled: !affordable, mode: 'buy' }
}

const getItemMetaLine = (item) => {
  if (currentDimension.value === 'GAIA') {
    return item.subcategory === 'vehicles'
      ? `GAIA 车辆 · 占地 ${item.grid_width || 1}x${item.grid_height || 1}`
      : `GAIA 建筑 · 占地 ${item.grid_width || 1}x${item.grid_height || 1}`
  }
  return item.placement_type === 'greenery' ? 'PHYSICAL 绿化单元' : 'PHYSICAL 建筑单元'
}

const animateToBlueprintVault = (sourceElement, itemName) => {
  const sourceRect = sourceElement?.getBoundingClientRect?.()
  const targetRect = document.querySelector('[data-blueprint-vault-anchor]')?.getBoundingClientRect?.()
  if (!sourceRect || !targetRect) return

  const packet = document.createElement('div')
  packet.className = 'vault-transfer-packet'
  packet.textContent = itemName || 'BLUEPRINT'
  packet.style.left = `${sourceRect.left + sourceRect.width / 2 - 64}px`
  packet.style.top = `${sourceRect.top + sourceRect.height / 2 - 20}px`
  document.body.appendChild(packet)

  requestAnimationFrame(() => {
    const deltaX = targetRect.left + targetRect.width / 2 - (sourceRect.left + sourceRect.width / 2)
    const deltaY = targetRect.top + targetRect.height / 2 - (sourceRect.top + sourceRect.height / 2)
    packet.style.transform = `translate(${deltaX}px, ${deltaY}px) scale(0.52)`
    packet.style.opacity = '0.08'
  })

  window.setTimeout(() => {
    packet.remove()
  }, 760)
}

const buyItem = async (item, triggerElement = null) => {
  if (purchasingId.value || !item.id) return
  if (!canAfford(item)) {
    feedbackMessage.value = `${getItemPrice(item).label}不足，无法购买 ${item.name_cn || item.name}`
    return
  }
  purchasingId.value = item.id
  feedbackMessage.value = ''
  try {
    const response = await unifiedShopApi.buy(username.value, item.id, 1)
    feedbackMessage.value = response.data.message || '购买成功，资产已写入工程装备仓。'
    animateToBlueprintVault(triggerElement, item.name_cn || item.name)
    await reloadShopState()
  } catch (error) {
    feedbackMessage.value = error.response?.data?.detail || '购买失败'
  } finally {
    purchasingId.value = null
  }
}

const sendToBackpackPlacement = async (item) => {
  let inventoryUnit = inventoryStore.beginPlacementFromCatalog(item)
  if (!inventoryUnit) {
    await inventoryStore.refreshInventory(username.value)
    inventoryUnit = inventoryStore.beginPlacementFromCatalog(item)
  }
  if (!inventoryUnit) {
    feedbackMessage.value = '装备仓中暂时没有可部署实体，请先购买后再试。'
    return
  }

  dimensionStore.setDimension(inventoryUnit.dimension)
  router.push('/')
}

const handlePrimaryAction = async (item, event = null) => {
  const action = getPrimaryAction(item)
  if (action.mode === 'buy') {
    await buyItem(item, event?.currentTarget || null)
  } else if (action.mode === 'place') {
    await sendToBackpackPlacement(item)
  }
}

const switchDimension = (dimension) => {
  activeFacet.value = 'all'
  previewItem.value = null
  feedbackMessage.value = ''
  dimensionStore.setDimension(dimension)
}

const handleRailSelect = (id) => {
  if (id === 'exchange') return
  if (id === 'protocol') {
    router.push('/exam')
    return
  }
  if (id === 'vault') {
    router.push('/')
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent('blueprint-vault-open'))
    }, 60)
    return
  }
  router.push('/')
}

const goBack = () => router.push('/')

watch(currentDimension, async () => {
  activeFacet.value = 'all'
  previewItem.value = null
  await reloadShopState()
})

onMounted(async () => {
  dimensionStore.rehydrate()
  await reloadShopState()
})
</script>

<template>
  <div class="shop-page">
    <NavRail active-id="exchange" @select="handleRailSelect" />

    <header class="shop-header kenney-hud-panel">
      <button type="button" class="back-btn kenney-hud-btn" @click="goBack">返回城市</button>
      <div class="title-wrap">
        <span class="title-icon">{{ currentDimension === 'GAIA' ? 'GAIA' : '3D' }}</span>
        <div>
          <h1>{{ composeWorldLabel(WORLD_NAMES.exchangePort) }}</h1>
          <p>统一账单驱动双维采购，购买成功后将以数据传输动画写入工程装备仓。</p>
        </div>
      </div>
      <div class="wallet">
        <div class="wallet-item">
          <span>{{ WORLD_NAMES.currency.zh }} · {{ WORLD_NAMES.currency.en }}</span>
          <strong>{{ userCoins }}</strong>
        </div>
        <div class="wallet-item">
          <span>专注能量</span>
          <strong>{{ userSunshine }}</strong>
        </div>
      </div>
    </header>

    <div class="dimension-tabs">
      <button
        v-for="tab in dimensionTabs"
        :key="tab.code"
        type="button"
        class="dimension-tab"
        :class="{ active: currentDimension === tab.code }"
        @click="switchDimension(tab.code)"
      >
        <strong>{{ tab.label }}</strong>
        <span>{{ tab.caption }}</span>
      </button>
    </div>

    <div class="toolbar">
      <input v-model="searchQuery" type="text" class="toolbar-input" placeholder="搜索名称、编号或主题词" />
      <select v-model="gradeFilter" class="toolbar-select">
        <option value="all">全部等级</option>
        <option value="legendary">Legendary</option>
        <option value="epic">Epic</option>
        <option value="rare">Rare</option>
        <option value="common">Common</option>
      </select>
      <select v-model="sortBy" class="toolbar-select">
        <option value="grade_desc">等级优先</option>
        <option value="price_asc">价格升序</option>
        <option value="price_desc">价格降序</option>
        <option value="name">名称排序</option>
      </select>
    </div>

    <div class="category-tabs">
      <button
        v-for="tab in categoryTabs"
        :key="tab.code"
        type="button"
        class="category-tab"
        :class="{ active: activeFacet === tab.code }"
        @click="activeFacet = tab.code"
      >
        {{ tab.label }}
      </button>
    </div>

    <p v-if="feedbackMessage" class="feedback-line">{{ feedbackMessage }}</p>

    <section class="items-grid">
      <article
        v-for="item in filteredItems"
        :key="item.item_code || item.id"
        class="item-card"
        :class="{ pending: item.sync_pending }"
      >
        <button type="button" class="preview-trigger" @click="previewItem = item">
          <div class="grade-badge">{{ String(item.grade || item.rarity || 'C').toUpperCase() }}</div>
          <div class="dimension-chip">{{ currentDimension }}</div>
          <div class="preview-art" :class="{ hologram: currentDimension === 'GAIA' }">
            <img v-if="item.preview_path" :src="item.preview_path" :alt="item.name_cn || item.name" />
            <span v-else class="preview-fallback">{{ currentDimension === 'GAIA' ? 'GAIA' : '3D' }}</span>
          </div>
          <div class="item-main">
            <h2>{{ item.name_cn || item.name }}</h2>
            <p>{{ getItemMetaLine(item) }}</p>
          </div>
        </button>

        <div class="item-stats">
          <span>总持有 {{ item.owned_count || 0 }}</span>
          <span>可放置 {{ item.available_to_place_count || 0 }}</span>
          <span>已部署 {{ item.placed_count || 0 }}</span>
          <span v-if="currentDimension === 'PHYSICAL'">槽位 {{ item.slot_capacity_remaining || 0 }}</span>
          <span v-else>占地 {{ item.grid_width || 1 }} x {{ item.grid_height || 1 }}</span>
        </div>

        <div class="item-footer">
          <div class="price-tag">
            <span>{{ getItemPrice(item).icon }}</span>
            <strong>{{ getItemPrice(item).amount }}</strong>
          </div>
          <button
            type="button"
            class="primary-btn"
            :disabled="getPrimaryAction(item).disabled || isPurchasing(item)"
            @click="handlePrimaryAction(item, $event)"
          >
            {{ isPurchasing(item) ? '处理中...' : getPrimaryAction(item).label }}
          </button>
        </div>
      </article>

      <div v-if="!isLoading && filteredItems.length === 0" class="empty-state">
        当前维度下没有符合筛选条件的资产。
      </div>
    </section>

    <div v-if="isLoading" class="loading-state">
      正在同步 {{ currentDimension }} 维度物质交换港...
    </div>

    <div v-if="previewItem" class="preview-overlay" @click.self="previewItem = null">
      <div class="preview-modal kenney-hud-panel">
        <button type="button" class="close-btn" @click="previewItem = null">×</button>
        <div class="preview-top">
          <div class="preview-art large" :class="{ hologram: currentDimension === 'GAIA' }">
            <img v-if="previewItem.preview_path" :src="previewItem.preview_path" :alt="previewItem.name_cn || previewItem.name" />
            <span v-else class="preview-fallback">{{ currentDimension === 'GAIA' ? 'GAIA' : '3D' }}</span>
          </div>
          <div class="preview-meta">
            <span class="grade-badge large">{{ String(previewItem.grade || previewItem.rarity || 'C').toUpperCase() }}</span>
            <span class="preview-dimension">{{ currentDimension }}</span>
            <h2>{{ previewItem.name_cn || previewItem.name }}</h2>
            <p>{{ previewItem.description || 'Twin-dimension city asset.' }}</p>
          </div>
        </div>

        <div class="preview-stats">
          <div><span>资产维度</span><strong>{{ currentDimension }}</strong></div>
          <div><span>部署类型</span><strong>{{ getItemMetaLine(previewItem) }}</strong></div>
          <div><span>背包可放</span><strong>{{ previewItem.available_to_place_count || 0 }}</strong></div>
          <div><span>价格</span><strong>{{ getItemPrice(previewItem).amount }} {{ getItemPrice(previewItem).label }}</strong></div>
        </div>

        <div class="preview-actions">
          <button
            type="button"
            class="primary-btn"
            :disabled="getPrimaryAction(previewItem).disabled || isPurchasing(previewItem)"
            @click="handlePrimaryAction(previewItem, $event)"
          >
            {{ isPurchasing(previewItem) ? '处理中...' : getPrimaryAction(previewItem).label }}
          </button>
          <button type="button" class="secondary-btn" @click="previewItem = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shop-page {
  position: relative;
  min-height: 100vh;
  box-sizing: border-box;
  padding: 20px;
  padding-bottom: 110px;
  background:
    radial-gradient(circle at 50% 12%, rgba(109, 92, 255, 0.22), transparent 24%),
    radial-gradient(circle at 80% 20%, rgba(76, 222, 255, 0.14), transparent 22%),
    linear-gradient(180deg, #030611 0%, #071022 44%, #0a192f 100%);
  color: #eef7ff;
}

.shop-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 24px;
  margin-bottom: 16px;
}

.back-btn {
  min-width: 118px;
}

.title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  min-width: 52px;
  font-size: 16px;
  font-weight: 800;
}

.title-wrap h1 {
  margin: 0;
  font-size: 28px;
  text-shadow: 0 0 16px rgba(0, 255, 255, 0.14);
}

.title-wrap p {
  margin: 4px 0 0;
  font-size: 13px;
  color: rgba(222, 240, 255, 0.72);
}

.wallet {
  display: flex;
  gap: 10px;
}

.wallet-item {
  min-width: 96px;
  border-radius: 16px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.wallet-item span {
  font-family: 'Roboto Mono', 'Consolas', monospace;
  font-size: 10px;
  color: rgba(196, 245, 255, 0.74);
}

.dimension-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.dimension-tab {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  border: 1px solid rgba(125, 220, 255, 0.18);
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.04);
  color: #eef7ff;
  cursor: pointer;
  text-align: left;
}

.dimension-tab.active {
  border-color: transparent;
  background: linear-gradient(180deg, rgba(47, 216, 255, 0.18), rgba(45, 116, 255, 0.2));
  box-shadow: inset 0 0 0 1px rgba(115, 224, 255, 0.24);
}

.dimension-tab span {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.7);
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.toolbar-input,
.toolbar-select {
  border: 1px solid rgba(125, 220, 255, 0.22);
  border-radius: 14px;
  background: rgba(10, 20, 46, 0.9);
  color: #eef7ff;
  padding: 12px 14px;
  outline: none;
}

.toolbar-input {
  flex: 1;
}

.category-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.category-tab {
  border: 1px solid rgba(125, 220, 255, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: #eef7ff;
  padding: 9px 14px;
  cursor: pointer;
}

.category-tab.active {
  background: linear-gradient(180deg, #2fd8ff, #2d74ff);
  border-color: transparent;
}

.feedback-line {
  margin: 0 0 12px;
  color: #9ce6ff;
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.item-card {
  border-radius: 22px;
  padding: 16px;
  background:
    linear-gradient(180deg, rgba(12, 27, 59, 0.96), rgba(7, 14, 32, 0.96)),
    rgba(12, 20, 42, 0.88);
  border: 1px solid rgba(125, 220, 255, 0.18);
  box-shadow: 0 18px 42px rgba(3, 8, 22, 0.34);
}

.item-card.pending {
  opacity: 0.74;
}

.preview-trigger {
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  position: relative;
}

.preview-art {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 140px;
  border-radius: 18px;
  background: rgba(5, 11, 26, 0.78);
  overflow: hidden;
}

.preview-art img {
  width: 100%;
  height: 140px;
  object-fit: contain;
}

.preview-art.hologram img {
  image-rendering: pixelated;
  mix-blend-mode: screen;
  filter: hue-rotate(180deg) saturate(1.2) brightness(1.15) drop-shadow(0 0 14px rgba(88, 228, 255, 0.28));
}

.preview-art.large img {
  height: 180px;
}

.preview-fallback {
  font-size: 48px;
}

.grade-badge,
.dimension-chip {
  position: absolute;
  top: 12px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.46);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-weight: 800;
}

.grade-badge {
  left: 12px;
  min-width: 34px;
  height: 34px;
  padding: 0 10px;
}

.dimension-chip {
  right: 12px;
  min-width: 64px;
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
}

.grade-badge.large {
  position: static;
  width: fit-content;
  min-width: 42px;
  height: 42px;
  margin-bottom: 12px;
}

.item-main {
  margin-top: 14px;
}

.item-main h2,
.preview-meta h2 {
  margin: 0;
  font-size: 18px;
}

.item-main p,
.preview-meta p,
.preview-dimension {
  margin: 6px 0 0;
  color: rgba(222, 240, 255, 0.68);
  font-size: 13px;
}

.preview-dimension {
  display: inline-block;
  margin-top: 0;
}

.item-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin: 14px 0;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.72);
}

.item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.price-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.primary-btn,
.secondary-btn {
  min-height: 42px;
  border: none;
  border-radius: 14px;
  padding: 0 16px;
  color: #eef7ff;
  font-weight: 800;
  cursor: pointer;
}

.primary-btn {
  background: linear-gradient(180deg, #2fd8ff, #2d74ff);
}

.secondary-btn {
  background: rgba(255, 255, 255, 0.08);
}

.primary-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.loading-state,
.empty-state {
  padding: 36px 18px;
  border-radius: 20px;
  text-align: center;
  background: rgba(255, 255, 255, 0.04);
}

.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(2, 5, 12, 0.62);
  backdrop-filter: blur(14px);
}

.preview-modal {
  position: relative;
  width: min(720px, calc(100vw - 32px));
  border-radius: 24px;
  padding: 20px;
}

.close-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  color: #eef7ff;
  font-size: 22px;
  cursor: pointer;
}

.preview-top {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 18px;
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin: 18px 0;
}

.preview-stats div {
  border-radius: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.04);
}

.preview-stats span {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.68);
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

:global(.vault-transfer-packet) {
  position: fixed;
  z-index: 70;
  width: 128px;
  min-height: 40px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(0, 255, 255, 0.14);
  border: 1px solid rgba(0, 255, 255, 0.4);
  color: #eefdff;
  font-family: 'Roboto Mono', 'Consolas', monospace;
  font-size: 10px;
  letter-spacing: 0.12em;
  box-shadow: 0 0 22px rgba(0, 255, 255, 0.22);
  pointer-events: none;
  transition: transform 0.72s cubic-bezier(0.2, 0.75, 0.15, 1), opacity 0.72s ease;
}

@media (max-width: 768px) {
  .shop-page {
    padding: 14px;
    padding-bottom: 120px;
  }

  .shop-header,
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .preview-top {
    display: flex;
    flex-direction: column;
  }

  .preview-stats {
    grid-template-columns: repeat(2, 1fr);
  }

  .dimension-tabs {
    grid-template-columns: 1fr;
  }
}
</style>
