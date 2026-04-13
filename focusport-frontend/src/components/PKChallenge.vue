<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import axios from 'axios'

const router = useRouter()
const userStore = useUserStore()
const API_BASE = 'http://127.0.0.1:8000'

const activePKs = ref([])
const pendingInvites = ref([])
const pkHistory = ref([])
const isLoading = ref(false)
const showCreateModal = ref(false)
const showInviteModal = ref(false)

const newPK = ref({
  type: 'focus',
  duration: 25,
  target_value: 60,
  opponent: ''
})

const pkTypes = [
  { key: 'focus', label: '专注时长', icon: '⏱️', unit: '分钟' },
  { key: 'tasks', label: '完成任务', icon: '✅', unit: '个' },
  { key: 'exp', label: '经验获取', icon: '⭐', unit: 'EXP' }
]

const loadPKData = async () => {
  isLoading.value = true
  try {
    const res = await axios.get(`${API_BASE}/api/pk/active/${userStore.username}`)
    activePKs.value = res.data.active || []
    pendingInvites.value = res.data.pending || []
    pkHistory.value = res.data.history || []
  } catch (error) {
    console.error('加载PK数据失败:', error)
  } finally {
    isLoading.value = false
  }
}

const createPK = async () => {
  if (!newPK.value.opponent) {
    alert('请输入对手用户名')
    return
  }

  try {
    const res = await axios.post(`${API_BASE}/api/pk/create`, {
      creator: userStore.username,
      opponent: newPK.value.opponent,
      type: newPK.value.type,
      duration: newPK.value.duration,
      target_value: newPK.value.target_value
    })
    alert('PK挑战已发送！')
    showCreateModal.value = false
    newPK.value = { type: 'focus', duration: 25, target_value: 60, opponent: '' }
    await loadPKData()
  } catch (error) {
    alert('创建失败: ' + (error.response?.data?.detail || error.message))
  }
}

const acceptPK = async (pkId) => {
  try {
    await axios.post(`${API_BASE}/api/pk/accept`, {
      pk_id: pkId,
      username: userStore.username
    })
    alert('已接受挑战！开始PK吧！')
    await loadPKData()
  } catch (error) {
    alert('接受失败: ' + (error.response?.data?.detail || error.message))
  }
}

const declinePK = async (pkId) => {
  try {
    await axios.post(`${API_BASE}/api/pk/decline`, {
      pk_id: pkId,
      username: userStore.username
    })
    await loadPKData()
  } catch (error) {
    console.error('拒绝失败:', error)
  }
}

const getPKTypeIcon = (type) => {
  return pkTypes.find(t => t.key === type)?.icon || '⚔️'
}

const getPKTypeLabel = (type) => {
  return pkTypes.find(t => t.key === type)?.label || type
}

const getTimeRemaining = (endTime) => {
  if (!endTime) return '--'
  const remaining = new Date(endTime) - new Date()
  if (remaining <= 0) return '已结束'
  const hours = Math.floor(remaining / 3600000)
  const mins = Math.floor((remaining % 3600000) / 60000)
  return `${hours}小时${mins}分钟`
}

const goBack = () => router.push('/')

onMounted(() => loadPKData())
</script>

<template>
  <div class="pk-container">
    <div class="pk-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>⚔️ PK挑战</h1>
      <button class="create-btn" @click="showCreateModal = true">发起PK</button>
    </div>

    <!-- 待处理邀请 -->
    <div v-if="pendingInvites.length > 0" class="section">
      <h2 class="section-title">📨 收到的挑战 ({{ pendingInvites.length }})</h2>
      <div class="pk-list">
        <div v-for="pk in pendingInvites" :key="pk.id" class="pk-card pending">
          <div class="pk-info">
            <span class="pk-icon">{{ getPKTypeIcon(pk.type) }}</span>
            <div class="pk-details">
              <div class="pk-opponent">
                <strong>{{ pk.creator }}</strong> 向你发起挑战
              </div>
              <div class="pk-type">
                {{ getPKTypeLabel(pk.type) }} · 剩余 {{ getTimeRemaining(pk.end_time) }}
              </div>
            </div>
          </div>
          <div class="pk-actions">
            <button class="accept-btn" @click="acceptPK(pk.id)">接受</button>
            <button class="decline-btn" @click="declinePK(pk.id)">拒绝</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 进行中的PK -->
    <div class="section">
      <h2 class="section-title">🔥 进行中的PK</h2>
      <div class="pk-list">
        <div v-for="pk in activePKs" :key="pk.id" class="pk-card active">
          <div class="pk-header-row">
            <span class="pk-icon large">{{ getPKTypeIcon(pk.type) }}</span>
            <div class="pk-players">
              <div class="player" :class="{ winning: pk.my_score > pk.opponent_score }">
                <span class="player-name">{{ pk.my_score > pk.opponent_score ? '👑 ' : '' }}{{ userStore.username }}</span>
                <span class="player-score">{{ pk.my_score || 0 }}</span>
              </div>
              <span class="vs">VS</span>
              <div class="player" :class="{ winning: pk.opponent_score > pk.my_score }">
                <span class="player-name">{{ pk.opponent_score > pk.my_score ? '👑 ' : '' }}{{ pk.opponent }}</span>
                <span class="player-score">{{ pk.opponent_score || 0 }}</span>
              </div>
            </div>
          </div>

          <div class="pk-progress">
            <div class="progress-bar">
              <div class="progress-fill my" :style="{ width: Math.min(50, (pk.my_score / (pk.my_score + pk.opponent_score || 1)) * 50) + '%' }"></div>
              <div class="progress-fill opponent" :style="{ width: Math.min(50, (pk.opponent_score / (pk.my_score + pk.opponent_score || 1)) * 50) + '%' }"></div>
            </div>
          </div>

          <div class="pk-meta">
            <span>{{ getPKTypeLabel(pk.type) }}</span>
            <span>⏰ {{ getTimeRemaining(pk.end_time) }}</span>
            <span v-if="pk.winner_exp">🏆 奖励 +{{ pk.winner_exp }} EXP</span>
          </div>
        </div>

        <div v-if="activePKs.length === 0" class="empty-state">
          <span class="empty-icon">🤝</span>
          <p>暂无进行中的PK</p>
          <button class="start-btn" @click="showCreateModal = true">发起第一个挑战</button>
        </div>
      </div>
    </div>

    <!-- 历史记录 -->
    <div class="section" v-if="pkHistory.length > 0">
      <h2 class="section-title">📜 历史记录</h2>
      <div class="history-list">
        <div v-for="pk in pkHistory" :key="pk.id" class="history-item" :class="pk.result">
          <span class="result-badge">{{ pk.result === 'win' ? '🏆 胜利' : pk.result === 'lose' ? '💔 失败' : '🤝 平局' }}</span>
          <span class="history-opponent">vs {{ pk.opponent }}</span>
          <span class="history-score">{{ pk.my_score }} : {{ pk.opponent_score }}</span>
          <span class="history-exp" v-if="pk.exp_gained">+{{ pk.exp_gained }} EXP</span>
        </div>
      </div>
    </div>

    <!-- 创建PK弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <h3>⚔️ 发起PK挑战</h3>

        <div class="form-group">
          <label>挑战对象</label>
          <input v-model="newPK.opponent" type="text" placeholder="输入对方用户名" />
        </div>

        <div class="form-group">
          <label>PK类型</label>
          <div class="type-selector">
            <button
              v-for="type in pkTypes"
              :key="type.key"
              :class="['type-btn', { active: newPK.type === type.key }]"
              @click="newPK.type = type.key"
            >
              <span class="type-icon">{{ type.icon }}</span>
              <span>{{ type.label }}</span>
            </button>
          </div>
        </div>

        <div class="form-group">
          <label>PK时长（小时）</label>
          <div class="duration-selector">
            <button
              v-for="d in [1, 6, 12, 24]"
              :key="d"
              :class="['duration-btn', { active: newPK.duration === d }]"
              @click="newPK.duration = d"
            >
              {{ d }}小时
            </button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="cancel-btn" @click="showCreateModal = false">取消</button>
          <button class="confirm-btn" @click="createPK">发起挑战</button>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.pk-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  color: white;
  padding-bottom: 100px;
}

.pk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  margin-bottom: 20px;
}

.back-btn, .create-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
}

.create-btn {
  background: rgba(239, 68, 68, 0.3);
  border-color: rgba(239, 68, 68, 0.5);
}

h1 { margin: 0; font-size: 24px; }

.section { margin-bottom: 24px; }

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: rgba(255, 255, 255, 0.9);
}

.pk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pk-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.pk-card.pending {
  background: rgba(251, 191, 36, 0.1);
  border-color: rgba(251, 191, 36, 0.3);
}

.pk-card.active {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.pk-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pk-icon {
  font-size: 24px;
}

.pk-icon.large {
  font-size: 36px;
}

.pk-details { flex: 1; }

.pk-opponent {
  font-size: 15px;
  font-weight: 500;
}

.pk-type {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 4px;
}

.pk-actions {
  display: flex;
  gap: 8px;
}

.accept-btn, .decline-btn {
  padding: 8px 16px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
}

.accept-btn {
  background: rgba(74, 222, 128, 0.3);
  color: white;
}

.decline-btn {
  background: rgba(248, 113, 113, 0.3);
  color: white;
}

.pk-header-row {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
}

.pk-players {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.player {
  text-align: center;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  min-width: 100px;
}

.player.winning {
  background: rgba(251, 191, 36, 0.2);
}

.player-name {
  display: block;
  font-size: 14px;
  font-weight: 500;
}

.player-score {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #4ade80;
}

.vs {
  font-size: 14px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.5);
}

.pk-progress {
  margin-bottom: 16px;
}

.progress-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  display: flex;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width 0.5s;
}

.progress-fill.my {
  background: #4ade80;
}

.progress-fill.opponent {
  background: #f87171;
}

.pk-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.start-btn {
  margin-top: 16px;
  background: rgba(239, 68, 68, 0.3);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: white;
  padding: 12px 24px;
  border-radius: 12px;
  cursor: pointer;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.history-item.win { background: rgba(74, 222, 128, 0.1); }
.history-item.lose { background: rgba(248, 113, 113, 0.1); }

.result-badge {
  font-size: 13px;
  font-weight: 500;
}

.history-opponent {
  flex: 1;
  font-size: 14px;
}

.history-score {
  font-weight: 600;
  font-size: 14px;
}

.history-exp {
  color: #fbbf24;
  font-size: 13px;
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: rgba(30, 40, 60, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 24px;
  width: 380px;
}

.modal-content h3 {
  margin: 0 0 20px 0;
  font-size: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: white;
  font-size: 15px;
  box-sizing: border-box;
}

.type-selector, .duration-selector {
  display: flex;
  gap: 8px;
}

.type-btn, .duration-btn {
  flex: 1;
  padding: 12px 8px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: white;
  cursor: pointer;
  font-size: 13px;
}

.type-btn.active, .duration-btn.active {
  background: rgba(239, 68, 68, 0.3);
  border-color: rgba(239, 68, 68, 0.5);
}

.type-icon {
  display: block;
  font-size: 20px;
  margin-bottom: 4px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.modal-actions button {
  flex: 1;
  padding: 14px;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.confirm-btn {
  background: rgba(239, 68, 68, 0.4);
  color: white;
}

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
  border-top-color: #ef4444;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
