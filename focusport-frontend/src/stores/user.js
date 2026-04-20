import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, growthApi } from '../api'
import { useFocusHubStore } from './focusHub'
import { useMasterTimelineStore } from './masterTimeline'

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
      console.error('加载成长数据失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function login(user, pass) {
    try {
      const res = await authApi.login(user, pass)
      username.value = user
      localStorage.setItem('username', user)
      await loadGrowth()
      return { success: true }
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || '登录失败' }
    }
  }

  function logout() {
    username.value = 'guest'
    localStorage.removeItem('username')
    growth.value = {
      exp: 0,
      level: 1,
      discipline_score: 50,
      streak_days: 0
    }
    try {
      const focusHubStore = useFocusHubStore()
      focusHubStore.clearTicker()
    } catch (e) { /* store not initialized yet */ }
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
    logout,
    expProgress,
    expToNextLevel
  }
})
