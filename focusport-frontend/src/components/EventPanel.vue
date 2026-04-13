<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { eventApi, checkinApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const events = ref([])
const checkinStatus = ref(null)
const isLoading = ref(false)

const loadEvents = async () => {
  isLoading.value = true
  try {
    const res = await eventApi.list(true)
    events.value = res.data.events || []
  } catch (error) {
    console.error('加载活动失败:', error)
  } finally {
    isLoading.value = false
  }
}

const loadCheckinStatus = async () => {
  try {
    const res = await checkinApi.status(userStore.username)
    checkinStatus.value = res.data
  } catch (error) {
    console.error('加载签到状态失败:', error)
  }
}

const doCheckin = async () => {
  try {
    const res = await checkinApi.checkin(userStore.username)
    if (res.data.success) {
      const days = res.data.consecutive_day || res.data.consecutive_days || 1
      const exp = res.data.reward_exp || res.data.exp_gained || 10
      alert(`签到成功！连续 ${days} 天，获得 ${exp} EXP`)
      await loadCheckinStatus()
      await userStore.loadGrowth()
    }
  } catch (error) {
    alert('签到失败: ' + (error.response?.data?.detail || '今日已签到'))
  }
}

const joinEvent = async (eventId) => {
  try {
    await eventApi.join(eventId)
    alert('已参加活动！')
    await loadEvents()
  } catch (error) {
    alert('参加失败: ' + (error.response?.data?.detail || error.message))
  }
}

const getEventIcon = (type) => {
  const icons = {
    focus: '⏱️',
    task: '📋',
    challenge: '⚔️',
    social: '👥',
    special: '🌟'
  }
  return icons[type] || '📌'
}

const getEventStatusClass = (event) => {
  if (!event.is_active) return 'ended'
  if (event.is_joined) return 'joined'
  return 'active'
}

const goBack = () => router.push('/')

onMounted(() => {
  loadEvents()
  loadCheckinStatus()
})
</script>

<template>
  <div class="event-container">
    <div class="event-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>🎉 活动 & 签到</h1>
      <div class="header-spacer"></div>
    </div>

    <!-- 每日签到卡片 -->
    <div class="checkin-card">
      <div class="checkin-info">
        <div class="checkin-icon">📅</div>
        <div class="checkin-details">
          <h3>每日签到</h3>
          <p v-if="checkinStatus">
            已连续签到 <strong>{{ checkinStatus.consecutive_day || 0 }}</strong> 天
            <span v-if="checkinStatus.today_checked"> · 今日已签到 ✅</span>
          </p>
        </div>
      </div>
      <button
        class="checkin-btn"
        :class="{ disabled: checkinStatus?.today_checked }"
        @click="doCheckin"
        :disabled="checkinStatus?.today_checked"
      >
        {{ checkinStatus?.today_checked ? '已签到' : '签到' }}
      </button>
    </div>

    <!-- 签到奖励预览 -->
    <div class="rewards-preview">
      <div class="reward-item" :class="{ active: checkinStatus?.consecutive_days >= 7 }">
        <span class="reward-day">7天</span>
        <span class="reward-icon">🎁</span>
        <span class="reward-exp">+100 EXP</span>
      </div>
      <div class="reward-item" :class="{ active: checkinStatus?.consecutive_days >= 14 }">
        <span class="reward-day">14天</span>
        <span class="reward-icon">🎁</span>
        <span class="reward-exp">+200 EXP</span>
      </div>
      <div class="reward-item" :class="{ active: checkinStatus?.consecutive_days >= 30 }">
        <span class="reward-day">30天</span>
        <span class="reward-icon">🎁</span>
        <span class="reward-exp">+500 EXP</span>
      </div>
    </div>

    <!-- 活动列表 -->
    <div class="section-title">🎯 进行中的活动</div>
    <div class="events-list">
      <div
        v-for="event in events"
        :key="event.id"
        :class="['event-card', getEventStatusClass(event)]"
      >
        <div class="event-header-row">
          <span class="event-icon">{{ getEventIcon(event.event_type) }}</span>
          <span :class="['event-status-badge', getEventStatusClass(event)]">
            {{ event.is_joined ? '已参加' : event.is_active ? '进行中' : '已结束' }}
          </span>
        </div>

        <h3 class="event-title">{{ event.name }}</h3>
        <p class="event-desc">{{ event.description }}</p>

        <div class="event-meta">
          <span>⏰ {{ event.end_time || '长期有效' }}</span>
          <span v-if="event.reward_exp">⭐ +{{ event.reward_exp }} EXP</span>
        </div>

        <div class="event-progress" v-if="event.is_joined && event.progress !== undefined">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: event.progress + '%' }"></div>
          </div>
          <span class="progress-text">{{ event.progress }}%</span>
        </div>

        <button
          v-if="event.is_active && !event.is_joined"
          class="join-btn"
          @click="joinEvent(event.id)"
        >
          立即参加
        </button>
      </div>

      <div v-if="events.length === 0" class="empty-state">
        <span class="empty-icon">📭</span>
        <p>暂无进行中的活动</p>
      </div>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.event-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  color: white;
}

.event-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
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

h1 { margin: 0; font-size: 24px; }
.header-spacer { width: 100px; }

.checkin-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  margin-bottom: 16px;
}

.checkin-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.checkin-icon { font-size: 40px; }

.checkin-details h3 { margin: 0 0 4px 0; font-size: 18px; }
.checkin-details p { margin: 0; font-size: 14px; color: rgba(255, 255, 255, 0.7); }

.checkin-btn {
  padding: 12px 32px;
  background: rgba(74, 222, 128, 0.3);
  border: 1px solid rgba(74, 222, 128, 0.5);
  color: white;
  border-radius: 14px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 600;
}

.checkin-btn.disabled {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  opacity: 0.7;
}

.rewards-preview {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.reward-item {
  flex: 1;
  text-align: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.reward-item.active {
  background: rgba(74, 222, 128, 0.15);
  border-color: rgba(74, 222, 128, 0.3);
}

.reward-day { display: block; font-size: 12px; color: rgba(255, 255, 255, 0.6); margin-bottom: 8px; }
.reward-icon { font-size: 24px; }
.reward-exp { display: block; font-size: 12px; color: #fbbf24; margin-top: 6px; }

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: rgba(255, 255, 255, 0.8);
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.event-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.event-card.joined {
  background: rgba(74, 222, 128, 0.1);
  border-color: rgba(74, 222, 128, 0.2);
}

.event-card.ended { opacity: 0.6; }

.event-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.event-icon { font-size: 28px; }

.event-status-badge {
  padding: 4px 12px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.event-status-badge.active { background: rgba(59, 130, 246, 0.25); color: #60a5fa; }
.event-status-badge.joined { background: rgba(74, 222, 128, 0.25); color: #4ade80; }
.event-status-badge.ended { background: rgba(107, 114, 128, 0.25); color: #9ca3af; }

.event-title { margin: 0 0 8px 0; font-size: 18px; }
.event-desc { margin: 0 0 12px 0; font-size: 14px; color: rgba(255, 255, 255, 0.7); }

.event-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 16px;
}

.event-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ade80, #22d3ee);
  transition: width 0.5s;
}

.progress-text { font-size: 13px; font-weight: 600; color: #4ade80; }

.join-btn {
  width: 100%;
  padding: 12px;
  background: rgba(74, 222, 128, 0.25);
  border: 1px solid rgba(74, 222, 128, 0.4);
  color: white;
  border-radius: 12px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
}

.join-btn:hover { background: rgba(74, 222, 128, 0.4); }

.empty-state { text-align: center; padding: 60px; }
.empty-icon { font-size: 48px; display: block; margin-bottom: 12px; }
.empty-state p { color: rgba(255, 255, 255, 0.6); }

.loading-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.spinner {
  width: 40px; height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
