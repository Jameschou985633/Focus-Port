<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { growthApi, statsApi, achievementApi, leaderboardApi } from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('username') || 'guest')

// 用户数据
const userGrowth = ref({
  focus_energy: 0,
  total_focus_minutes: 0,
  streak_days: 0
})

// 当前Tab
const activeTab = ref('overview')

// 统计数据
const weeklyData = ref([])
const achievements = ref([])
const leaderboard = ref([])

// 计算等级 (每60分钟升一级)
const userLevel = computed(() => {
  return Math.max(1, Math.floor(userGrowth.value.total_focus_minutes / 60))
})

// 加载用户数据
const loadUserGrowth = async () => {
  try {
    const res = await growthApi.get(username.value)
    if (res.data.growth) {
      userGrowth.value = res.data.growth
    }
  } catch (error) {
    console.error('加载用户数据失败:', error)
  }
}

// 加载周数据
const loadWeeklyData = async () => {
  try {
    const res = await statsApi.get(username.value, 'week')
    weeklyData.value = res.data.daily_stats || []
  } catch (error) {
    console.error('加载周数据失败:', error)
  }
}

// 加载成就
const loadAchievements = async () => {
  try {
    const res = await achievementApi.user(username.value)
    achievements.value = res.data.achievements || []
  } catch (error) {
    console.error('加载成就失败:', error)
  }
}

// 加载排行榜
const loadLeaderboard = async () => {
  try {
    const res = await leaderboardApi.get('focus', 'week')
    leaderboard.value = res.data.leaderboard || []
  } catch (error) {
    console.error('加载排行榜失败:', error)
  }
}

const goBack = () => router.push('/')

onMounted(() => {
  loadUserGrowth()
  loadWeeklyData()
  loadAchievements()
  loadLeaderboard()
})
</script>

<template>
  <div class="stats-panel">
    <!-- 顶部状态栏 -->
    <div class="stats-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>📊 统计</h1>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-icon">⚡</span>
          <span class="stat-value">{{ userGrowth.focus_energy }}</span>
        </div>
      </div>
    </div>

    <!-- 核心数据卡片 -->
    <div class="core-stats">
      <div class="stat-card level-card">
        <div class="card-icon">⭐</div>
        <div class="card-content">
          <div class="card-value">Lv.{{ userLevel }}</div>
          <div class="card-label">当前等级</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="card-icon">⏱️</div>
        <div class="card-content">
          <div class="card-value">{{ Math.floor(userGrowth.total_focus_minutes / 60) }}h</div>
          <div class="card-label">专注时长</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="card-icon">🔥</div>
        <div class="card-content">
          <div class="card-value">{{ userGrowth.streak_days }}</div>
          <div class="card-label">连续天数</div>
        </div>
      </div>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button :class="['tab-btn', { active: activeTab === 'overview' }]" @click="activeTab = 'overview'">
        📈 概览
      </button>
      <button :class="['tab-btn', { active: activeTab === 'achievements' }]" @click="activeTab = 'achievements'">
        🎖️ 成就
      </button>
      <button :class="['tab-btn', { active: activeTab === 'ranking' }]" @click="activeTab = 'ranking'">
        🏆 排行
      </button>
    </div>

    <!-- Tab 内容 -->
    <div class="tab-content">
      <!-- 概览 -->
      <div v-if="activeTab === 'overview'" class="overview-content">
        <div class="section-card">
          <h3>本周专注</h3>
          <div class="week-chart">
            <div v-for="(day, index) in weeklyData" :key="index" class="day-bar">
              <div class="bar-fill" :style="{ height: Math.min(100, (day.focus_minutes || 0) / 2) + '%' }"></div>
              <span class="day-label">{{ ['日', '一', '二', '三', '四', '五', '六'][index] }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 成就 -->
      <div v-if="activeTab === 'achievements'" class="achievements-content">
        <div class="achievement-grid">
          <div v-for="ach in achievements" :key="ach.code" class="achievement-card" :class="{ unlocked: ach.unlocked }">
            <span class="ach-icon">{{ ach.icon || '🏅' }}</span>
            <span class="ach-name">{{ ach.name }}</span>
          </div>
        </div>
        <div v-if="achievements.length === 0" class="empty-state">
          <p>暂无成就数据</p>
        </div>
      </div>

      <!-- 排行榜 -->
      <div v-if="activeTab === 'ranking'" class="ranking-content">
        <div class="ranking-list">
          <div v-for="(user, index) in leaderboard" :key="user.username" class="ranking-item">
            <span class="rank">{{ index + 1 }}</span>
            <span class="username">{{ user.username }}</span>
            <span class="score">{{ user.total_focus_minutes }}分钟</span>
          </div>
        </div>
        <div v-if="leaderboard.length === 0" class="empty-state">
          <p>暂无排行数据</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-panel {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  padding-bottom: 100px;
  color: white;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  margin-bottom: 20px;
}

.back-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
}

h1 {
  margin: 0;
  font-size: 20px;
}

.header-stats {
  display: flex;
  gap: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(251, 191, 36, 0.2);
  padding: 8px 14px;
  border-radius: 12px;
}

.stat-value {
  font-weight: 600;
}

/* 核心数据卡片 */
.core-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 20px;
  text-align: center;
}

.level-card {
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.card-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
}

.card-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 4px;
}

/* Tab 切换 */
.tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tab-btn {
  flex: 1;
  padding: 14px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 14px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: rgba(74, 222, 128, 0.25);
  border-color: rgba(74, 222, 128, 0.5);
}

/* Tab 内容 */
.tab-content {
  min-height: 300px;
}

.section-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 20px;
  margin-bottom: 16px;
}

.section-card h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
}

/* 周图表 */
.week-chart {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 120px;
  padding-top: 20px;
}

.day-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.bar-fill {
  width: 20px;
  background: linear-gradient(to top, #4ade80, #22d3ee);
  border-radius: 10px;
  min-height: 4px;
}

.day-label {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

/* 成就网格 */
.achievement-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.achievement-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 16px;
  text-align: center;
  opacity: 0.5;
}

.achievement-card.unlocked {
  opacity: 1;
  background: rgba(251, 191, 36, 0.15);
}

.ach-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
}

.ach-name {
  font-size: 12px;
}

/* 排行榜 */
.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ranking-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.ranking-item:first-child {
  background: rgba(251, 191, 36, 0.2);
}

.rank {
  width: 24px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.5);
}

.ranking-item:first-child .rank {
  color: #fbbf24;
}

.username {
  flex: 1;
}

.score {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.5);
}
</style>
