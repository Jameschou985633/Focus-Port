import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const LEGACY_STORAGE_KEY = 'dimensionMode'
const ACTIVE_DIMENSION_PREFIX = 'fc.activeDimension.'
const TRANSITION_MS = 420
const TRANSITION_SWAP_MS = 180

export const normalizeActiveDimension = (value) => {
  if (value === '3D' || value === 'PHYSICAL') return 'PHYSICAL'
  return 'GAIA'
}

export const activeToLegacyDimension = (value) => (
  normalizeActiveDimension(value) === 'PHYSICAL' ? '3D' : '2D'
)

export const legacyToActiveDimension = (value) => (
  value === '3D' ? 'PHYSICAL' : 'GAIA'
)

const currentUsername = () => {
  if (typeof window === 'undefined') return 'guest'
  return window.localStorage.getItem('username') || 'guest'
}

const modernStorageKey = (username = currentUsername()) => `${ACTIVE_DIMENSION_PREFIX}${username}`

const readStoredDimension = (username = currentUsername()) => {
  if (typeof window === 'undefined') return 'PHYSICAL'
  const modern = window.localStorage.getItem(modernStorageKey(username))
  if (modern) return normalizeActiveDimension(modern)
  const legacy = window.localStorage.getItem(LEGACY_STORAGE_KEY)
  return legacy ? legacyToActiveDimension(legacy) : 'PHYSICAL'
}

export const useDimensionStore = defineStore('dimension', () => {
  const activeDimension = ref(readStoredDimension())
  const isTransitioning = ref(false)
  const transitionTarget = ref(activeDimension.value)

  let releaseTimer = null
  let swapTimer = null

  const currentDimension = computed(() => activeToLegacyDimension(activeDimension.value))
  const isPhysical = computed(() => activeDimension.value === 'PHYSICAL')
  const isGaia = computed(() => activeDimension.value === 'GAIA')
  const preview3DVisible = computed(() => isGaia.value)
  const currentDimensionLabel = computed(() => (
    isPhysical.value
      ? composeWorldLabel(WORLD_NAMES.physical)
      : composeWorldLabel(WORLD_NAMES.gaia)
  ))

  const persistDimension = (dimension, username = currentUsername()) => {
    if (typeof window === 'undefined') return
    const normalized = normalizeActiveDimension(dimension)
    window.localStorage.setItem(modernStorageKey(username), normalized)
    window.localStorage.setItem(LEGACY_STORAGE_KEY, activeToLegacyDimension(normalized))
  }

  const applyDimension = (dimension, username = currentUsername()) => {
    const normalized = normalizeActiveDimension(dimension)
    activeDimension.value = normalized
    transitionTarget.value = normalized
    persistDimension(normalized, username)
  }

  const setDimension = (next, username = currentUsername()) => {
    applyDimension(next, username)
  }

  const playDimensionTransition = (next, username = currentUsername()) => {
    const normalized = normalizeActiveDimension(next)
    if (isTransitioning.value || normalized === activeDimension.value) return

    if (releaseTimer) window.clearTimeout(releaseTimer)
    if (swapTimer) window.clearTimeout(swapTimer)

    isTransitioning.value = true
    transitionTarget.value = normalized

    swapTimer = window.setTimeout(() => {
      applyDimension(normalized, username)
    }, TRANSITION_SWAP_MS)

    releaseTimer = window.setTimeout(() => {
      isTransitioning.value = false
    }, TRANSITION_MS)
  }

  const toggleDimension = (username = currentUsername()) => {
    playDimensionTransition(isPhysical.value ? 'GAIA' : 'PHYSICAL', username)
  }

  const rehydrate = (username = currentUsername()) => {
    applyDimension(readStoredDimension(username), username)
  }

  return {
    activeDimension,
    currentDimension,
    currentDimensionLabel,
    isPhysical,
    isGaia,
    isTransitioning,
    preview3DVisible,
    transitionTarget,
    rehydrate,
    setDimension,
    toggleDimension,
    playDimensionTransition
  }
})
