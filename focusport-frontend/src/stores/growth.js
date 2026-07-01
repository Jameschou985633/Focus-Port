import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { statsApi, leaderboardApi, achievementApi } from '../api'

export const useGrowthStore = defineStore('growth', () => {
  // Daily stats
  const dailyStats = ref([])
  const weeklySummary = ref({
    totalFocusMinutes: 0,
    totalTasks: 0,
    totalExp: 0,
    avgDiscipline: 50
  })

  // Leaderboard
  const leaderboard = ref([])
  const userRank = ref(null)

  // Achievements
  const achievements = ref([])
  const userAchievements = ref([])

  // Loading states
  const isLoadingStats = ref(false)
  const isLoadingLeaderboard = ref(false)

  // Actions
  async function loadDailyStats(username, days = 7) {
    isLoadingStats.value = true
    try {
      const period = days <= 1 ? 'day' : days <= 7 ? 'week' : days <= 30 ? 'month' : 'year'
      const res = await statsApi.get(username, period)
      if (res.data) {
        dailyStats.value = res.data.daily_stats || []
        weeklySummary.value = res.data.summary || weeklySummary.value
      }
    } catch (error) {
      console.error('加载统计数据失败:', error)
    } finally {
      isLoadingStats.value = false
    }
  }

  async function loadLeaderboard(type = 'global', category = 'exp', period = 'weekly') {
    isLoadingLeaderboard.value = true
    try {
      const res = await leaderboardApi.get(type, category, period)
      if (res.data) {
        leaderboard.value = res.data.rankings || []
        userRank.value = res.data.user_rank
      }
    } catch (error) {
      console.error('加载排行榜失败:', error)
    } finally {
      isLoadingLeaderboard.value = false
    }
  }

  async function loadAchievements() {
    try {
      const res = await achievementApi.all()
      achievements.value = res.data.achievements || []
    } catch (error) {
      console.error('加载成就失败:', error)
    }
  }

  async function loadUserAchievements(username) {
    try {
      const res = await achievementApi.user(username)
      userAchievements.value = res.data.unlocked || []
    } catch (error) {
      console.error('加载用户成就失败:', error)
    }
  }

  // Computed
  const totalFocusHours = computed(() => {
    return Math.round(weeklySummary.value.totalFocusMinutes / 60 * 10) / 10
  })

  const achievementProgress = computed(() => {
    if (achievements.value.length === 0) return 0
    return Math.round(userAchievements.value.length / achievements.value.length * 100)
  })

  return {
    dailyStats,
    weeklySummary,
    leaderboard,
    userRank,
    achievements,
    userAchievements,
    isLoadingStats,
    isLoadingLeaderboard,
    loadDailyStats,
    loadLeaderboard,
    loadAchievements,
    loadUserAchievements,
    totalFocusHours,
    achievementProgress
  }
})
