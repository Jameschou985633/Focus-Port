<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useGrowthStore } from '../stores/growth'
import { statsApi } from '../api'

const router = useRouter()
const userStore = useUserStore()
const growthStore = useGrowthStore()

const selectedPeriod = ref('week')
const isLoading = ref(false)

// 统计数据
const summary = ref({
  totalFocusHours: 0,
  totalTasks: 0,
  totalExp: 0,
  avgDiscipline: 50,
  streakDays: 0
})

// 每日数据
const dailyData = ref([])

// 加载统计
const loadStats = async () => {
  isLoading.value = true
  try {
    const res = await statsApi.get(userStore.username, selectedPeriod.value)
    if (res.data) {
      dailyData.value = res.data.daily_stats || []
      summary.value = res.data.summary || summary.value
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  } finally {
    isLoading.value = false
  }
}

// 返回岛屿
const goBack = () => {
  router.push('/')
}

onMounted(() => {
  loadStats()
})
</script>

<template>
  <div class="dashboard-container">
    <!-- 顶部导航 -->
    <div class="dashboard-header">
      <button class="back-btn" @click="goBack">← 返回岛屿</button>
      <h1>📊 学习数据仪表盘</h1>
      <div class="period-tabs">
        <button :class="{ active: selectedPeriod === 'week' }" @click="selectedPeriod = 'week'; loadStats()">周</button>
        <button :class="{ active: selectedPeriod === 'month' }" @click="selectedPeriod = 'month'; loadStats()">月</button>
        <button :class="{ active: selectedPeriod === 'year' }" @click="selectedPeriod = 'year'; loadStats()">年</button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card focus">
        <span class="stat-icon">⏱️</span>
        <span class="stat-value">{{ summary.totalFocusHours.toFixed(1) }}</span>
        <span class="stat-label">专注小时</span>
      </div>
      <div class="stat-card tasks">
        <span class="stat-icon">✅</span>
        <span class="stat-value">{{ summary.totalTasks }}</span>
        <span class="stat-label">完成任务</span>
      </div>
      <div class="stat-card exp">
        <span class="stat-icon">⭐</span>
        <span class="stat-value">{{ summary.totalExp }}</span>
        <span class="stat-label">获得经验</span>
      </div>
      <div class="stat-card streak">
        <span class="stat-icon">🔥</span>
        <span class="stat-value">{{ summary.streakDays }}</span>
        <span class="stat-label">连续天数</span>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <div class="chart-card">
        <h3>📈 专注时长趋势</h3>
        <div class="chart-placeholder">
          <div class="simple-chart">
            <div v-for="(day, index) in dailyData" :key="index" class="chart-bar" :style="{ height: (day.focus_minutes / 60 / 2 * 100) + '%' }">
              <span class="bar-label">{{ day.focus_minutes }}分钟</span>
            </div>
          </div>
        </div>
      </div>

      <div class="chart-card">
        <h3>🎯 自律指数</h3>
        <div class="discipline-gauge">
          <div class="gauge-value">{{ Math.round(summary.avgDiscipline) }}</div>
          <div class="gauge-bar">
            <div class="gauge-fill" :style="{ width: summary.avgDiscipline + '%' }"></div>
          </div>
          <div class="gauge-label">
            {{ summary.avgDiscipline >= 80 ? '优秀' : summary.avgDiscipline >= 60 ? '良好' : summary.avgDiscipline >= 40 ? '一般' : '需改进' }}
          </div>
        </div>
      </div>

      <div class="chart-card wide">
        <h3>📅 每日专注分布</h3>
        <div class="daily-grid">
          <div v-for="(day, index) in dailyData" :key="index" class="day-cell">
            <div class="day-label">{{ day.stat_date?.slice(5) || '-' }}</div>
            <div class="day-intensity" :style="{ opacity: Math.min(1, day.focus_minutes / 120) }"></div>
            <div class="day-value">{{ Math.round(day.focus_minutes / 60 * 10) / 10 }}h</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 20px;
  color: white;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
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

.period-tabs {
  display: flex;
  gap: 8px;
}

.period-tabs button {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 8px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.period-tabs button.active {
  background: rgba(74, 222, 128, 0.3);
  border-color: rgba(74, 222, 128, 0.5);
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 24px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.stat-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 36px;
  font-weight: 800;
  display: block;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.stat-card.focus .stat-value { color: #4ade80; }
.stat-card.tasks .stat-value { color: #60a5fa; }
.stat-card.exp .stat-value { color: #fbbf24; }
.stat-card.streak .stat-value { color: #f87171; }

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.chart-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.chart-card.wide {
  grid-column: span 2;
}

.chart-card h3 {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
}

.chart-placeholder {
  height: 200px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.simple-chart {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 100%;
  width: 100%;
}

.chart-bar {
  flex: 1;
  background: linear-gradient(180deg, #4ade80, #22c55e);
  border-radius: 8px 8px 0 0;
  min-height: 10px;
  max-height: 180px;
  position: relative;
  transition: height 0.5s ease;
}

.bar-label {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  margin-bottom: 4px;
}

.discipline-gauge {
  text-align: center;
  padding: 20px;
}

.gauge-value {
  font-size: 64px;
  font-weight: 800;
  color: #4ade80;
  margin-bottom: 16px;
}

.gauge-bar {
  height: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 12px;
}

.gauge-fill {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #f59e0b, #4ade80);
  border-radius: 6px;
  transition: width 0.5s ease;
}

.gauge-label {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.daily-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}

.day-cell {
  text-align: center;
  padding: 8px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
}

.day-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
}

.day-intensity {
  height: 40px;
  background: #4ade80;
  border-radius: 6px;
  margin-bottom: 4px;
}

.day-value {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.8);
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

@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-grid {
    grid-template-columns: 1fr;
  }
  .chart-card.wide {
    grid-column: span 1;
  }
}
</style>
