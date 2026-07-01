import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, growthApi } from '../api'
import { useFocusHubStore } from './focusHub'
import { useMasterTimelineStore } from './masterTimeline'
import { useDimensionStore } from './dimension'
import { useInventoryStore } from './inventory'
import { useTaskStore } from './useTaskStore'

export const useUserStore = defineStore('user', () => {
  // State
  const username = ref(localStorage.getItem('username') || 'guest')
  const isLoggedIn = computed(() => username.value !== 'guest')

  // Growth data
  const growth = ref({
    exp: 0,
    level: 1,
    discipline_score: 50,
    streak_days: 0,
    max_streak: 0,
    total_focus_minutes: 0,
    total_trees: 0,
    achievements_count: 0
  })

  // Loading states
  const isLoading = ref(false)
  const lastFetch = ref(null)

  const defaultGrowth = () => ({
    exp: 0,
    level: 1,
    discipline_score: 50,
    streak_days: 0,
    max_streak: 0,
    total_focus_minutes: 0,
    total_trees: 0,
    achievements_count: 0
  })

  function syncAccountStores(nextUsername) {
    const scopedUsername = nextUsername || 'guest'

    try {
      useFocusHubStore().hydrate(scopedUsername)
    } catch (e) { /* store not initialized yet */ }

    try {
      useMasterTimelineStore().hydrateToday(scopedUsername)
    } catch (e) { /* store not initialized yet */ }

    try {
      useDimensionStore().rehydrate(scopedUsername)
    } catch (e) { /* store not initialized yet */ }

    try {
      const inventoryStore = useInventoryStore()
      inventoryStore.hydrateForUser(scopedUsername)
      inventoryStore.resetPlacementState()
    } catch (e) { /* store not initialized yet */ }

    try {
      useTaskStore().hydrateForUser(scopedUsername)
    } catch (e) { /* store not initialized yet */ }
  }

  async function switchAccount(nextUsername) {
    const scopedUsername = String(nextUsername || '').trim()
    if (!scopedUsername) return
    username.value = scopedUsername
    localStorage.setItem('username', scopedUsername)
    growth.value = defaultGrowth()
    lastFetch.value = null
    syncAccountStores(scopedUsername)
    await loadGrowth()
  }

  // Actions
  async function loadGrowth() {
    if (!username.value) return

    isLoading.value = true
    try {
      const res = await growthApi.get(username.value)
      if (res.data.growth) {
        growth.value = res.data.growth
        lastFetch.value = Date.now()
      }
    } catch (error) {
      console.error('鍔犺浇鎴愰暱鏁版嵁澶辫触:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function login(user, pass) {
    try {
      const res = await authApi.login(user, pass)
      await switchAccount(user)
      return { success: true }
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || '鐧诲綍澶辫触' }
    }
  }

  function logout() {
    username.value = 'guest'
    localStorage.removeItem('username')
    growth.value = defaultGrowth()
    lastFetch.value = null
    try {
      const focusHubStore = useFocusHubStore()
      focusHubStore.clearTicker()
    } catch (e) { /* store not initialized yet */ }
    syncAccountStores('guest')
  }

  // Computed
  const expProgress = computed(() => {
    const nextLevel = growth.value.level * 100
    return growth.value.exp / nextLevel
  })

  const expToNextLevel = computed(() => {
    return growth.value.level * 100
  })

  return {
    username,
    isLoggedIn,
    growth,
    isLoading,
    lastFetch,
    loadGrowth,
    login,
    switchAccount,
    syncAccountStores,
    logout,
    expProgress,
    expToNextLevel
  }
})
