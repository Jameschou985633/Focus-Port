<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { leaderboardApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const rankings = ref([])
const userRank = ref(null)
const isLoading = ref(false)

const activeTab = ref('exp')  // exp, focus, streak
const activePeriod = ref('weekly')  // daily, weekly, monthly

const tabs = [
  { key: 'exp', label: '经验榜', icon: '⭐' },
  { key: 'focus', label: '专注榜', icon: '⏱️' },
  { key: 'streak', label: '连续榜', icon: '🔥' }
]

const periods = [
  { key: 'daily', label: '今日' },
  { key: 'weekly', label: '本周' },
  { key: 'monthly', label: '本月' }
]

const loadLeaderboard = async () => {
  isLoading.value = true
  try {
    const res = await leaderboardApi.get('global', activeTab.value, activePeriod.value)
    if (res.data) {
      rankings.value = res.data.rankings || []
      userRank.value = res.data.user_rank
    }
  } catch (error) {
    console.error('加载排行榜失败:', error)
  } finally {
    isLoading.value = false
  }
}

const goBack = () => {
  router.push('/')
}

const getRankStyle = (index) => {
  if (index === 0) return { color: '#ffd700', icon: '🥇' }
  if (index === 1) return { color: '#c0c0c0', icon: '🥈' }
  if (index === 2) return { color: '#cd7f32', icon: '🥉' }
  return { color: '#ffffff', icon: '' }
}

onMounted(() => {
  loadLeaderboard()
})
</script>

<template>
  <div class="leaderboard-container">
    <!-- 顶部导航 -->
    <div class="leaderboard-header">
      <button class="back-btn" @click="goBack">← 返回岛屿</button>
      <h1>🏆 排行榜</h1>
      <div class="header-spacer"></div>
    </div>

    <!-- 分类标签 -->
    <div class="tabs-container">
      <div class="category-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-btn', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key; loadLeaderboard()"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          <span>{{ tab.label }}</span>
        </button>
      </div>

      <div class="period-tabs">
        <button
          v-for="period in periods"
          :key="period.key"
          :class="['period-btn', { active: activePeriod === period.key }]"
          @click="activePeriod = period.key; loadLeaderboard()"
        >
          {{ period.label }}
        </button>
      </div>
    </div>

    <!-- 前三名展示 -->
    <div class="top-three">
      <div class="top-item second" v-if="rankings[1]">
        <div class="top-avatar">🥈</div>
        <div class="top-name">{{ rankings[1].username }}</div>
        <div class="top-score">{{ rankings[1].score }}</div>
      </div>
      <div class="top-item first" v-if="rankings[0]">
        <div class="top-crown">👑</div>
        <div class="top-avatar">🥇</div>
        <div class="top-name">{{ rankings[0].username }}</div>
        <div class="top-score">{{ rankings[0].score }}</div>
      </div>
      <div class="top-item third" v-if="rankings[2]">
        <div class="top-avatar">🥉</div>
        <div class="top-name">{{ rankings[2].username }}</div>
        <div class="top-score">{{ rankings[2].score }}</div>
      </div>
    </div>

    <!-- 排行榜列表 -->
    <div class="rank-list">
      <div
        v-for="(item, index) in rankings.slice(3)"
        :key="item.username"
        class="rank-item"
        :class="{ isMe: item.username === userStore.username }"
      >
        <span class="rank-number">{{ index + 4 }}</span>
        <span class="rank-avatar">👤</span>
        <span class="rank-name">{{ item.username }}</span>
        <span class="rank-score">{{ item.score }}</span>
      </div>

      <div v-if="rankings.length === 0" class="empty-state">
        <p>暂无排行数据</p>
      </div>
    </div>

    <!-- 我的排名 -->
    <div class="my-rank" v-if="userRank">
      <span class="my-rank-label">我的排名</span>
      <span class="my-rank-value">#{{ userRank.rank }}</span>
      <span class="my-rank-score">{{ userRank.score }} 分</span>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.leaderboard-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 20px;
  color: white;
  padding-bottom: 100px;
}

.leaderboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
}

.back-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.header-spacer {
  width: 100px;
}

.tabs-container {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 16px;
  margin-bottom: 20px;
}

.category-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 12px;
  border-radius: 14px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.tab-btn.active {
  background: rgba(74, 222, 128, 0.25);
  border-color: rgba(74, 222, 128, 0.5);
}

.tab-icon {
  font-size: 18px;
}

.period-tabs {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.period-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.7);
  padding: 8px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.period-btn.active {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.top-three {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 24px;
  padding: 20px;
}

.top-item {
  text-align: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  min-width: 100px;
}

.top-item.first {
  transform: scale(1.15);
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(255, 193, 7, 0.1));
  border: 2px solid rgba(255, 215, 0, 0.4);
}

.top-item.second {
  background: linear-gradient(135deg, rgba(192, 192, 192, 0.2), rgba(176, 176, 176, 0.1));
  border: 1px solid rgba(192, 192, 192, 0.3);
}

.top-item.third {
  background: linear-gradient(135deg, rgba(205, 127, 50, 0.2), rgba(184, 115, 51, 0.1));
  border: 1px solid rgba(205, 127, 50, 0.3);
}

.top-crown {
  font-size: 24px;
  margin-bottom: 4px;
}

.top-avatar {
  font-size: 36px;
  margin-bottom: 8px;
}

.top-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.top-score {
  font-size: 18px;
  font-weight: 700;
  color: #4ade80;
}

.rank-list {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 16px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 14px;
  transition: background 0.2s;
}

.rank-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.rank-item.isMe {
  background: rgba(74, 222, 128, 0.15);
  border: 1px solid rgba(74, 222, 128, 0.3);
}

.rank-number {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  font-weight: 600;
  font-size: 14px;
}

.rank-avatar {
  font-size: 20px;
}

.rank-name {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
}

.rank-score {
  font-size: 16px;
  font-weight: 700;
  color: #4ade80;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.5);
}

.my-rank {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(30, 40, 60, 0.95);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(74, 222, 128, 0.5);
  border-radius: 20px;
  padding: 16px 32px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.my-rank-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.my-rank-value {
  font-size: 24px;
  font-weight: 800;
  color: #4ade80;
}

.my-rank-score {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
