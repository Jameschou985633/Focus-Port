import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { unifiedShopApi } from '../api'
import { activeToLegacyDimension, legacyToActiveDimension, normalizeActiveDimension } from './dimension'

const ACTIVE_DIMENSION_PREFIX = 'fc'

const currentUsername = () => {
  if (typeof window === 'undefined') return 'guest'
  return window.localStorage.getItem('username') || 'guest'
}

const storageKey = (scope, username = currentUsername()) => `${ACTIVE_DIMENSION_PREFIX}.${scope}.${username}`

const safeParseArray = (rawValue) => {
  if (!rawValue) return []
  try {
    const parsed = JSON.parse(rawValue)
    return Array.isArray(parsed) ? parsed : []
  } catch (error) {
    console.warn(`Failed to parse stored array: ${rawValue}`, error)
    return []
  }
}

const normalizePlacementType = (value, category = '', subcategory = '') => {
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
  if (subcategory === 'vehicles') return 'building'
  if (category === 'structures') return 'building'
  if (category === 'vehicles') return 'building'
  if (['plants', 'trees', 'greenery'].includes(category)) return 'greenery'
  if (['paths', 'roads'].includes(category)) return 'building'
  return 'building'
}

const toBackendDimension = (value) => activeToLegacyDimension(normalizeActiveDimension(value))
const toActiveDimension = (value) => legacyToActiveDimension(value)

const inferActiveDimension = (item = {}, fallback = {}) => {
  const mapId = item.map_id || item.mapId || fallback.mapId || ''
  const slotId = item.slot_id || item.slotId || fallback.slotId || ''
  const gridX = item.grid_x ?? item.gridX ?? fallback.gridX
  const gridY = item.grid_y ?? item.gridY ?? fallback.gridY
  const assetPath = String(
    item.asset_path ||
    item.assetPath ||
    item.preview_path ||
    item.previewPath ||
    item.sprite_path ||
    item.spritePath ||
    item.model_path ||
    item.modelPath ||
    fallback.assetPath ||
    fallback.previewPath ||
    fallback.spritePath ||
    fallback.modelPath ||
    ''
  )
  const modelPath = String(item.model_path || item.modelPath || fallback.modelPath || '')
  const explicitDimension = item.dimension || fallback.dimension

  if (
    mapId === 'city' ||
    Boolean(slotId) ||
    modelPath.includes('/city-assets/') ||
    modelPath.includes('/models/') ||
    modelPath.endsWith('.obj') ||
    modelPath.endsWith('.glb')
  ) {
    return 'PHYSICAL'
  }

  if (mapId === 'isometric-city' || gridX !== undefined || gridY !== undefined || assetPath.includes('/assets/2d/')) {
    return 'GAIA'
  }

  if (explicitDimension) {
    return toActiveDimension(explicitDimension)
  }

  return 'PHYSICAL'
}

const normalizeInventoryUnit = (item, fallback = {}) => {
  const dimension = inferActiveDimension(item, fallback)
  const backendDimension = toBackendDimension(dimension)
  const itemId = Number(item.item_id || item.itemId || item.id || fallback.itemId || 0)
  const itemCode = item.item_code || item.itemCode || fallback.itemCode || ''

  return {
    inventoryId: String(item.inventory_id || item.inventoryId || `local-${dimension}-${itemCode || itemId}`),
    itemId,
    itemCode,
    assetId: itemCode || fallback.assetId || `asset-${itemId || 'unknown'}`,
    name: item.name || fallback.name || itemCode || 'Unknown Asset',
    nameCn: item.name_cn || item.nameCn || fallback.nameCn || item.name || itemCode || 'Unknown Asset',
    dimension,
    backendDimension,
    assetPath: item.asset_path || item.assetPath || item.preview_path || item.previewPath || item.sprite_path || item.spritePath || item.model_path || item.modelPath || fallback.assetPath || '',
    previewPath: item.preview_path || item.previewPath || fallback.previewPath || item.asset_path || item.assetPath || '',
    spritePath: item.sprite_path || item.spritePath || fallback.spritePath || '',
    modelPath: item.model_path || item.modelPath || fallback.modelPath || '',
    placementType: normalizePlacementType(
      item.placement_type || item.placementType || fallback.placementType,
      item.category || fallback.category,
      item.subcategory || fallback.subcategory
    ),
    category: item.category || fallback.category || 'structures',
    subcategory: item.subcategory || fallback.subcategory || '',
    gridWidth: Math.max(1, Number(item.grid_width || item.gridWidth || fallback.gridWidth || 1)),
    gridHeight: Math.max(1, Number(item.grid_height || item.gridHeight || fallback.gridHeight || 1)),
    grade: item.grade || fallback.grade || 'C',
    rarity: item.rarity || fallback.rarity || 'common',
    footprint: {
      width: Math.max(1, Number(item.grid_width || item.gridWidth || fallback.gridWidth || 1)),
      height: Math.max(1, Number(item.grid_height || item.gridHeight || fallback.gridHeight || 1))
    },
    raw: item
  }
}

const normalizePlacedItem = (item, fallback = {}) => {
  const dimension = inferActiveDimension(item, fallback)
  const backendDimension = toBackendDimension(dimension)
  const itemId = Number(item.item_id || item.itemId || item.id || fallback.itemId || 0)
  const itemCode = item.item_code || item.itemCode || fallback.itemCode || ''
  const gridWidth = Math.max(1, Number(item.grid_width || item.gridWidth || fallback.gridWidth || 1))
  const gridHeight = Math.max(1, Number(item.grid_height || item.gridHeight || fallback.gridHeight || 1))

  return {
    id: String(item.id || fallback.id || `placed-${itemCode || itemId}`),
    username: item.username || fallback.username || currentUsername(),
    dimension,
    backendDimension,
    position: {
      x: Number(item.position_x ?? item.position?.x ?? fallback.position?.x ?? 0),
      y: Number(item.position_y ?? item.position?.y ?? fallback.position?.y ?? 0),
      z: Number(item.position_z ?? item.position?.z ?? fallback.position?.z ?? 0),
      gridX: Number(item.grid_x ?? item.position?.gridX ?? fallback.position?.gridX ?? 0),
      gridY: Number(item.grid_y ?? item.position?.gridY ?? fallback.position?.gridY ?? 0)
    },
    rotation: {
      y: Number(item.rotation_y ?? item.rotation?.y ?? fallback.rotation?.y ?? 0)
    },
    assetPath: item.asset_path || item.assetPath || item.preview_path || item.previewPath || item.sprite_path || item.spritePath || item.model_path || item.modelPath || fallback.assetPath || '',
    assetId: fallback.assetId || itemCode || `asset-${itemId || 'unknown'}`,
    itemId,
    itemCode,
    footprint: {
      width: gridWidth,
      height: gridHeight
    },
    previewPath: item.preview_path || item.previewPath || fallback.previewPath || '',
    spritePath: item.sprite_path || item.spritePath || fallback.spritePath || '',
    modelPath: item.model_path || item.modelPath || fallback.modelPath || '',
    name: item.name || fallback.name || itemCode || 'Placed Asset',
    nameCn: item.name_cn || item.nameCn || fallback.nameCn || item.name || itemCode || 'Placed Asset',
    category: item.category || fallback.category || 'structures',
    subcategory: item.subcategory || fallback.subcategory || '',
    placementType: normalizePlacementType(
      item.placement_type || item.placementType || fallback.placementType,
      item.category || fallback.category,
      item.subcategory || fallback.subcategory
    ),
    slotId: item.slot_id || item.slotId || fallback.slotId || '',
    mapId: item.map_id || item.mapId || fallback.mapId || (backendDimension === '3D' ? 'city' : 'isometric-city'),
    scale: Number(item.scale ?? fallback.scale ?? 1),
    raw: item
  }
}

export const useInventoryStore = defineStore('inventory', () => {
  const hydratedUsername = ref('')
  const userInventory = ref([])
  const placedItems = ref([])
  const placementMode = ref('IDLE')
  const placementDraft = ref(null)
  const ghostPreview = ref(null)
  const selectedInventoryItemId = ref('')
  const isLoadingInventory = ref(false)
  const isLoadingPlacedItems = ref(false)

  const inventoryByDimension = computed(() => ({
    GAIA: userInventory.value.filter((item) => item.dimension === 'GAIA'),
    PHYSICAL: userInventory.value.filter((item) => item.dimension === 'PHYSICAL')
  }))

  const placedByDimension = computed(() => ({
    GAIA: placedItems.value.filter((item) => item.dimension === 'GAIA'),
    PHYSICAL: placedItems.value.filter((item) => item.dimension === 'PHYSICAL')
  }))

  const isPlacing = computed(() => Boolean(placementDraft.value))
  const isPlacingGaia = computed(() => placementDraft.value?.dimension === 'GAIA' && isPlacing.value)
  const isPlacingPhysical = computed(() => placementDraft.value?.dimension === 'PHYSICAL' && isPlacing.value)

  const persistState = (scope, payload, username = hydratedUsername.value || currentUsername()) => {
    if (typeof window === 'undefined' || !username) return
    window.localStorage.setItem(storageKey(scope, username), JSON.stringify(payload))
  }

  const hydrateForUser = (username = currentUsername()) => {
    if (typeof window === 'undefined') return
    if (hydratedUsername.value === username) return

    userInventory.value = safeParseArray(window.localStorage.getItem(storageKey('userInventory', username)))
      .map((item) => normalizeInventoryUnit(item, item))
    placedItems.value = safeParseArray(window.localStorage.getItem(storageKey('placedItems', username)))
      .map((item) => normalizePlacedItem(item, item))
    hydratedUsername.value = username
  }

  watch(userInventory, (nextValue) => {
    if (!hydratedUsername.value) return
    persistState('userInventory', nextValue, hydratedUsername.value)
  }, { deep: true })

  watch(placedItems, (nextValue) => {
    if (!hydratedUsername.value) return
    persistState('placedItems', nextValue, hydratedUsername.value)
  }, { deep: true })

  const settlePlacementMode = (mode) => {
    placementMode.value = mode
    if (typeof window !== 'undefined') {
      window.setTimeout(() => {
        if (!placementDraft.value && placementMode.value === mode) {
          placementMode.value = 'IDLE'
        }
      }, 220)
    }
  }

  const resetPlacementState = (mode = 'IDLE') => {
    placementDraft.value = null
    ghostPreview.value = null
    selectedInventoryItemId.value = ''
    placementMode.value = mode
  }

  const findAvailableUnit = (catalogItem = null) => {
    if (!catalogItem) return null
    const normalizedDimension = inferActiveDimension(catalogItem, catalogItem)
    return userInventory.value.find((unit) => (
      unit.dimension === normalizedDimension &&
      (
        (catalogItem.inventoryId && unit.inventoryId === String(catalogItem.inventoryId)) ||
        (catalogItem.inventory_id && unit.inventoryId === String(catalogItem.inventory_id)) ||
        (catalogItem.item_code && unit.itemCode === catalogItem.item_code) ||
        (catalogItem.itemCode && unit.itemCode === catalogItem.itemCode) ||
        (catalogItem.id && unit.itemId === Number(catalogItem.id)) ||
        (catalogItem.item_id && unit.itemId === Number(catalogItem.item_id)) ||
        (catalogItem.model_path && unit.modelPath === catalogItem.model_path)
      )
    )) || null
  }

  const beginPlacement = (inventoryItem) => {
    const normalized = normalizeInventoryUnit(inventoryItem, inventoryItem)
    placementDraft.value = normalized
    selectedInventoryItemId.value = normalized.inventoryId
    ghostPreview.value = null
    placementMode.value = 'PLACEMENT_MODE'
    return normalized
  }

  const beginPlacementFromCatalog = (catalogItem) => {
    hydrateForUser()
    const existingUnit = findAvailableUnit(catalogItem)
    if (!existingUnit) return null
    return beginPlacement(existingUnit)
  }

  const consumeLegacyPendingPlacement = () => {
    if (typeof window === 'undefined') return null
    const raw = window.localStorage.getItem('pendingCityPlacementItem')
    if (!raw) return null

    try {
      const parsed = JSON.parse(raw)
      const existingUnit = findAvailableUnit(parsed)
      window.localStorage.removeItem('pendingCityPlacementItem')
      return beginPlacement(existingUnit || parsed)
    } catch (error) {
      console.warn('Failed to consume legacy placement payload', error)
      window.localStorage.removeItem('pendingCityPlacementItem')
      return null
    }
  }

  const updateGhostPreview = (payload = {}) => {
    if (!placementDraft.value) return
    ghostPreview.value = {
      ...(ghostPreview.value || {}),
      ...payload,
      dimension: placementDraft.value.dimension
    }
    placementMode.value = 'PREVIEWING'
  }

  const cancelPlacement = () => {
    placementDraft.value = null
    ghostPreview.value = null
    selectedInventoryItemId.value = ''
    settlePlacementMode('CANCELLED')
  }

  const removeInventoryUnit = (sourceItem = null) => {
    if (!sourceItem) return
    if (sourceItem.inventoryId) {
      userInventory.value = userInventory.value.filter((item) => item.inventoryId !== String(sourceItem.inventoryId))
      return
    }
    const matchIndex = userInventory.value.findIndex((item) => (
      item.dimension === sourceItem.dimension &&
      (
        (sourceItem.itemCode && item.itemCode === sourceItem.itemCode) ||
        (sourceItem.itemId && item.itemId === sourceItem.itemId)
      )
    ))
    if (matchIndex >= 0) {
      userInventory.value.splice(matchIndex, 1)
    }
  }

  const upsertPlacedItem = (placedItem) => {
    const nextItem = normalizePlacedItem(placedItem, placementDraft.value || {})
    const nextItems = placedItems.value.filter((item) => item.id !== nextItem.id)
    nextItems.push(nextItem)
    nextItems.sort((left, right) => String(left.id).localeCompare(String(right.id), undefined, { numeric: true }))
    placedItems.value = nextItems
    return nextItem
  }

  const completePlacement = (placedItem, sourceItem = placementDraft.value) => {
    const normalizedPlaced = upsertPlacedItem(placedItem)
    removeInventoryUnit(sourceItem)
    resetPlacementState('CONFIRMED')
    settlePlacementMode('CONFIRMED')
    return normalizedPlaced
  }

  const restoreInventoryFromPlaced = (placedItem) => {
    if (!placedItem) return
    const normalizedPlaced = normalizePlacedItem(placedItem, placedItem)
    const restored = normalizeInventoryUnit({
      inventory_id: `restored-${normalizedPlaced.id}`,
      id: normalizedPlaced.itemId,
      item_code: normalizedPlaced.itemCode,
      name: normalizedPlaced.name,
      name_cn: normalizedPlaced.nameCn,
      dimension: normalizedPlaced.backendDimension,
      preview_path: normalizedPlaced.previewPath,
      sprite_path: normalizedPlaced.spritePath,
      model_path: normalizedPlaced.modelPath,
      category: normalizedPlaced.category,
      subcategory: normalizedPlaced.subcategory,
      placement_type: normalizedPlaced.placementType,
      grid_width: normalizedPlaced.footprint.width,
      grid_height: normalizedPlaced.footprint.height
    })
    userInventory.value = [restored, ...userInventory.value]
  }

  const handlePlacedItemRemoval = (placedItem) => {
    const targetId = String(placedItem?.id || '')
    if (!targetId) return
    const existing = placedItems.value.find((item) => item.id === targetId)
    placedItems.value = placedItems.value.filter((item) => item.id !== targetId)
    restoreInventoryFromPlaced(existing || placedItem)
  }

  const replacePlacedItemsForDimension = (dimension, items) => {
    const normalizedDimension = normalizeActiveDimension(dimension)
    const normalizedItems = (items || []).map((item) => normalizePlacedItem(item))
    const otherItems = placedItems.value.filter((item) => item.dimension !== normalizedDimension)
    placedItems.value = [...otherItems, ...normalizedItems]
  }

  const refreshInventory = async (username = currentUsername()) => {
    hydrateForUser(username)
    isLoadingInventory.value = true
    try {
      const response = await unifiedShopApi.inventory(username)
      const incoming = (response.data?.items || [])
        .filter((item) => item.status === 'owned')
        .map((item) => normalizeInventoryUnit(item))
      userInventory.value = incoming
      return incoming
    } catch (error) {
      console.error('Failed to refresh inventory', error)
      return userInventory.value
    } finally {
      isLoadingInventory.value = false
    }
  }

  const refreshPlacedItems = async (username = currentUsername()) => {
    hydrateForUser(username)
    isLoadingPlacedItems.value = true
    try {
      const response = await unifiedShopApi.placed(username)
      const incoming = (response.data?.items || []).map((item) => normalizePlacedItem(item))
      placedItems.value = incoming
      return incoming
    } catch (error) {
      console.error('Failed to refresh placed items', error)
      return placedItems.value
    } finally {
      isLoadingPlacedItems.value = false
    }
  }

  const bootstrap = async (username = currentUsername()) => {
    hydrateForUser(username)
    await Promise.all([
      refreshInventory(username),
      refreshPlacedItems(username)
    ])
    return {
      inventory: userInventory.value,
      placed: placedItems.value
    }
  }

  return {
    userInventory,
    placedItems,
    placementMode,
    placementDraft,
    ghostPreview,
    selectedInventoryItemId,
    isLoadingInventory,
    isLoadingPlacedItems,
    inventoryByDimension,
    placedByDimension,
    isPlacing,
    isPlacingGaia,
    isPlacingPhysical,
    toBackendDimension,
    toActiveDimension,
    hydrateForUser,
    bootstrap,
    refreshInventory,
    refreshPlacedItems,
    beginPlacement,
    beginPlacementFromCatalog,
    consumeLegacyPendingPlacement,
    updateGhostPreview,
    cancelPlacement,
    completePlacement,
    handlePlacedItemRemoval,
    replacePlacedItemsForDimension,
    findAvailableUnit,
    resetPlacementState
  }
})
