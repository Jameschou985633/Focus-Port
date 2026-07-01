<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { unifiedShopApi } from '../../api'
import { useDimensionStore } from '../../stores/dimension'
import { useInventoryStore } from '../../stores/inventory'
import { useUserStore } from '../../stores/user'
import { WORLD_NAMES, composeWorldLabel } from '../../constants/worldNames'
import '../../assets/focus-hud.css'

const router = useRouter()
const route = useRoute()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()
const userStore = useUserStore()
const username = computed(() => userStore.username || 'guest')

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
const previewAttempts = ref(new Map())
const catalogScrollRef = ref(null)
const isCatalogDragging = ref(false)
const suppressCatalogClick = ref(false)
const catalogDrag = {
  pointerId: null,
  startY: 0,
  startScrollTop: 0,
  moved: false
}

const gradeOrder = { legendary: 5, epic: 4, rare: 3, common: 2, c: 1, b: 2, a: 3, s: 4 }
const isImagePath = (value) => /\.(png|jpe?g|webp|gif|svg)$/i.test(String(value || ''))
const uniqueValues = (values) => [...new Set(values.filter(Boolean))]

const getPreviewKey = (item) => String(item?.item_code || item?.id || item?.model_path || item?.preview_path || '')
const getPreviewCandidates = (item) => uniqueValues([item?.preview_path, ...(item?.preview_candidates || [])].filter((path) => isImagePath(path)))
const getPreviewSrc = (item) => {
  const candidates = getPreviewCandidates(item)
  const attempt = previewAttempts.value.get(getPreviewKey(item)) || 0
  return candidates[attempt] || ''
}
const hasPreview = (item) => Boolean(getPreviewSrc(item))
const markPreviewError = (item) => {
  const key = getPreviewKey(item)
  const next = new Map(previewAttempts.value)
  next.set(key, (next.get(key) || 0) + 1)
  previewAttempts.value = next
}

const currentDimension = computed(() => dimensionStore.activeDimension)
const normalizeShopDimension = (value) => {
  const raw = Array.isArray(value) ? value[0] : value
  const normalized = String(raw || '').trim().toUpperCase()
  if (['PHYSICAL', '3D'].includes(normalized)) return 'PHYSICAL'
  return ''
}

const dimensionTabs = [
  { code: 'PHYSICAL', label: composeWorldLabel(WORLD_NAMES.physical), caption: '3D 实体模型与槽位部署' },
]

const categoryTabs = computed(() => (
  currentDimension.value === 'GAIA'
    ? [
        { code: 'all', label: '全部' },
        { code: 'buildings', label: '建筑' },
        { code: 'vehicles', label: '车辆' }
      ]
    : [
        { code: 'all', label: '全部' }
      ]
))

const mergedItems = computed(() => {
  return backendItems.value.map((entry) => {
    const backendEntry = entry
    const isGaia = currentDimension.value === 'GAIA'

    return {
      id: backendEntry?.id ?? null,
      item_code: backendEntry?.item_code,
      name: backendEntry?.name || entry.name,
      name_cn: backendEntry?.name_cn || entry.name,
      preview_path: backendEntry?.preview_path || '',
      sprite_path: backendEntry?.sprite_path || '',
      model_path: backendEntry?.model_path || '',
      category: backendEntry?.category || entry.category || 'structures',
      subcategory: backendEntry?.subcategory || entry.subcategory || (isGaia ? 'buildings' : 'commercial'),
      placement_type: backendEntry?.placement_type || (entry.subcategory === 'vehicles' ? 'vehicle' : 'building'),
      grid_width: backendEntry?.grid_width || 1,
      grid_height: backendEntry?.grid_height || 1,
      rarity: backendEntry?.rarity || entry.rarity || 'common',
      grade: backendEntry?.grade || backendEntry?.rarity || entry.rarity || 'common',
      available_to_place_count: backendEntry?.available_to_place_count || 0,
      placed_count: backendEntry?.placed_count || 0,
      owned_count: backendEntry?.owned_count || 0,
      slot_capacity_remaining: backendEntry?.slot_capacity_remaining || 0,
      price_coins: backendEntry?.price_coins ?? 0,
      price_sunshine: backendEntry?.price_sunshine ?? 0,
      description: backendEntry?.description || (isGaia ? 'GAIA 模拟资产' : '3D 实体建筑资产'),
      dimension: currentDimension.value,
      sync_pending: !backendEntry?.id
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
  router.push({ path: '/island', query: { dimension: inventoryUnit.dimension } })
}

const handlePrimaryAction = async (item, event = null) => {
  const action = getPrimaryAction(item)
  if (action.mode === 'buy') {
    await buyItem(item, event?.currentTarget || null)
  } else if (action.mode === 'place') {
    await sendToBackpackPlacement(item)
  }
}

const canStartCatalogDrag = (target) => {
  const element = target instanceof Element ? target : null
  if (!element) return false
  return !element.closest('.primary-btn, .secondary-btn, .toolbar-input, .toolbar-select, .category-tab, .dimension-tab, .back-btn, .close-btn')
}

const startCatalogDrag = (event) => {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  if (!canStartCatalogDrag(event.target)) return
  const scroller = catalogScrollRef.value
  if (!scroller || scroller.scrollHeight <= scroller.clientHeight) return

  catalogDrag.pointerId = event.pointerId
  catalogDrag.startY = event.clientY
  catalogDrag.startScrollTop = scroller.scrollTop
  catalogDrag.moved = false
  isCatalogDragging.value = false
  scroller.setPointerCapture?.(event.pointerId)
}

const moveCatalogDrag = (event) => {
  if (catalogDrag.pointerId !== event.pointerId) return
  const scroller = catalogScrollRef.value
  if (!scroller) return

  const deltaY = event.clientY - catalogDrag.startY
  if (Math.abs(deltaY) > 4) {
    catalogDrag.moved = true
    isCatalogDragging.value = true
    suppressCatalogClick.value = true
  }
  if (!catalogDrag.moved) return

  event.preventDefault()
  scroller.scrollTop = catalogDrag.startScrollTop - deltaY
}

const endCatalogDrag = (event) => {
  if (catalogDrag.pointerId !== event.pointerId) return
  catalogScrollRef.value?.releasePointerCapture?.(event.pointerId)
  catalogDrag.pointerId = null
  window.setTimeout(() => {
    isCatalogDragging.value = false
    suppressCatalogClick.value = false
  }, 0)
}

const handleCatalogClickCapture = (event) => {
  if (!suppressCatalogClick.value) return
  event.preventDefault()
  event.stopPropagation()
}

const scrollCatalogToTop = async () => {
  await nextTick()
  requestAnimationFrame(() => {
    catalogScrollRef.value?.scrollTo?.({ top: 0, behavior: 'smooth' })
  })
}

const setActiveFacet = async (facet) => {
  activeFacet.value = facet
  await scrollCatalogToTop()
}

const switchDimension = (dimension) => {
  activeFacet.value = 'all'
  previewItem.value = null
  feedbackMessage.value = ''
  dimensionStore.setDimension(dimension)
  scrollCatalogToTop()
}

const goBack = () => {
  dimensionStore.setDimension('PHYSICAL')
  router.push({ path: '/island', query: { dimension: 'PHYSICAL' } })
}

watch(currentDimension, async () => {
  activeFacet.value = 'all'
  previewItem.value = null
  await reloadShopState()
})

watch(username, async () => {
  purchasingId.value = null
  previewItem.value = null
  feedbackMessage.value = ''
  await reloadShopState()
})

onMounted(async () => {
  dimensionStore.setDimension('PHYSICAL')
  const queryDimension = normalizeShopDimension(route.query.dimension)
  if (queryDimension) {
    dimensionStore.setDimension(queryDimension)
  }
  await reloadShopState()
})
</script>

<template>
  <div class="shop-page">
    <header class="shop-header focus-hud-panel">
      <button type="button" class="back-btn focus-hud-btn" @click="goBack">返回城市</button>
      <div class="title-wrap">
        <span class="title-icon">{{ currentDimension === 'GAIA' ? 'GAIA' : '3D' }}</span>
        <div>
          <h1>{{ composeWorldLabel(WORLD_NAMES.exchangePort) }}</h1>
          <p>统一账单驱动双维采购，购买成功后将写入工程装备仓。</p>
        </div>
      </div>
      <div class="wallet">
        <div class="wallet-item">
          <span>{{ WORLD_NAMES.currency.zh }} 路 {{ WORLD_NAMES.currency.en }}</span>
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
        @click="setActiveFacet(tab.code)"
      >
        {{ tab.label }}
      </button>
    </div>

    <p v-if="feedbackMessage" class="feedback-line">{{ feedbackMessage }}</p>

    <section
      ref="catalogScrollRef"
      class="items-grid"
      :class="{ dragging: isCatalogDragging }"
      @pointerdown="startCatalogDrag"
      @pointermove="moveCatalogDrag"
      @pointerup="endCatalogDrag"
      @pointercancel="endCatalogDrag"
      @click.capture="handleCatalogClickCapture"
    >
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
            <img v-if="hasPreview(item)" :src="getPreviewSrc(item)" :alt="item.name_cn || item.name" @error="markPreviewError(item)" />
            <span v-else class="preview-fallback">{{ currentDimension === 'GAIA' ? 'GAIA' : '3D 模型暂无预览' }}</span>
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
      <div class="preview-modal focus-hud-panel">
        <button type="button" class="close-btn" @click="previewItem = null">×</button>
        <div class="preview-top">
          <div class="preview-art large" :class="{ hologram: currentDimension === 'GAIA' }">
            <img v-if="hasPreview(previewItem)" :src="getPreviewSrc(previewItem)" :alt="previewItem.name_cn || previewItem.name" @error="markPreviewError(previewItem)" />
            <span v-else class="preview-fallback">{{ currentDimension === 'GAIA' ? 'GAIA' : '3D 模型暂无预览' }}</span>
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
  height: 100dvh;
  min-height: 100dvh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  padding: 20px;
  padding-bottom: 20px;
  overflow: hidden;
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
  flex: 0 0 auto;
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
  flex: 0 0 auto;
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
  flex: 0 0 auto;
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
  flex: 0 0 auto;
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
  flex: 0 0 auto;
  margin: 0 0 12px;
  color: #9ce6ff;
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  align-content: start;
  gap: 16px;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  padding-right: 8px;
  padding-bottom: 88px;
  cursor: grab;
  user-select: none;
  touch-action: pan-y;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: rgba(115, 224, 255, 0.5) rgba(10, 25, 47, 0.55);
}

.items-grid.dragging {
  cursor: grabbing;
}

.items-grid.dragging :is(.item-card, .preview-trigger) {
  cursor: grabbing;
}

.items-grid::-webkit-scrollbar {
  width: 8px;
}

.items-grid::-webkit-scrollbar-track {
  border-radius: 999px;
  background: rgba(10, 25, 47, 0.55);
}

.items-grid::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(115, 224, 255, 0.5);
}

.items-grid::-webkit-scrollbar-thumb:hover {
  background: rgba(115, 224, 255, 0.72);
}

.item-card {
  border-radius: 22px;
  padding: 16px;
  background:
    linear-gradient(180deg, rgba(12, 27, 59, 0.96), rgba(7, 14, 32, 0.96)),
    rgba(12, 20, 42, 0.88);
  border: 1px solid rgba(125, 220, 255, 0.18);
  box-shadow: 0 18px 42px rgba(3, 8, 22, 0.34);
  user-select: none;
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
  user-select: none;
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
  grid-column: 1 / -1;
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
    padding-bottom: 14px;
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
