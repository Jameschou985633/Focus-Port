<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { messageApi, friendApi } from '../api'
import SpaceButton from './base/SpaceButton.vue'

const router = useRouter()
const userStore = useUserStore()

const messages = ref([])
const unread = ref(0)
const loading = ref(false)
const activeTab = ref('all') // all | friend | system
const selectedMsg = ref(null)
const showCompose = ref(false)
const composeForm = ref({ receiver: '', title: '', content: '' })
const composeSending = ref(false)
const friends = ref([])

const tabs = [
  { value: 'all', label: '全部', icon: '📬' },
  { value: 'friend', label: '好友', icon: '👥' },
  { value: 'system', label: '系统', icon: '📢' }
]

const filteredMessages = computed(() => {
  if (activeTab.value === 'all') return messages.value
  return messages.value.filter(m => m.category === activeTab.value)
})

const loadMessages = async () => {
  loading.value = true
  try {
    const [msgRes, unreadRes] = await Promise.all([
      messageApi.list(userStore.username),
      messageApi.unread(userStore.username)
    ])
    messages.value = msgRes.data.messages || []
    unread.value = unreadRes.data.unread || 0
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    loading.value = false
  }
}

const loadFriends = async () => {
  try {
    const res = await friendApi.list(userStore.username)
    friends.value = res.data.friends?.filter(f => f.status === 'accepted') || []
  } catch (e) {
    console.error('加载好友列表失败:', e)
  }
}

const openMessage = async (msg) => {
  if (!msg.is_read) {
    try {
      await messageApi.markRead(msg.id)
      msg.is_read = true
      unread.value = Math.max(0, unread.value - 1)
    } catch (e) {
      console.error('标记已读失败:', e)
    }
  }
  selectedMsg.value = msg
}

const closeMessage = () => {
  selectedMsg.value = null
}

const markAllRead = async () => {
  try {
    await messageApi.markAllRead(userStore.username)
    messages.value.forEach(m => { m.is_read = true })
    unread.value = 0
  } catch (e) {
    console.error('全部已读失败:', e)
  }
}

const deleteMessage = async (msg) => {
  if (!confirm('确定删除这条消息？')) return
  try {
    await messageApi.delete(msg.id)
    messages.value = messages.value.filter(m => m.id !== msg.id)
    if (selectedMsg.value?.id === msg.id) selectedMsg.value = null
    if (!msg.is_read) unread.value = Math.max(0, unread.value - 1)
  } catch (e) {
    console.error('删除失败:', e)
  }
}

const sendCompose = async () => {
  const { receiver, title, content } = composeForm.value
  if (!receiver.trim() || !title.trim() || !content.trim()) {
    alert('请填写完整信息')
    return
  }
  composeSending.value = true
  try {
    await messageApi.send(userStore.username, receiver.trim(), title.trim(), content.trim())
    showCompose.value = false
    composeForm.value = { receiver: '', title: '', content: '' }
    alert('发送成功！')
    loadMessages()
  } catch (e) {
    alert('发送失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    composeSending.value = false
  }
}

const selectFriend = (friend) => {
  composeForm.value.receiver = friend.friend_username
}

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diff = now - d
  const min = Math.floor(diff / 60000)
  const hr = Math.floor(diff / 3600000)
  const day = Math.floor(diff / 86400000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min}分钟前`
  if (hr < 24) return `${hr}小时前`
  if (day < 7) return `${day}天前`
  return d.toLocaleDateString('zh-CN')
}

const categoryLabel = (cat) => {
  if (cat === 'system') return '系统通知'
  if (cat === 'friend') return '好友消息'
  return cat
}

const goBack = () => router.push('/more')

// Auto-refresh every 30s
let refreshTimer = null
onMounted(() => {
  loadMessages()
  loadFriends()
  refreshTimer = setInterval(loadMessages, 30000)
})
onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="mail-page">
    <header class="mail-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>📬 星际信箱</h1>
      <div class="header-actions">
        <span v-if="unread > 0" class="unread-badge">{{ unread }}</span>
        <SpaceButton variant="primary" size="sm" @click="showCompose = true">写消息</SpaceButton>
      </div>
    </header>

    <!-- Tabs -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        :class="['tab-btn', { active: activeTab === tab.value }]"
        @click="activeTab = tab.value"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        {{ tab.label }}
      </button>
      <button v-if="unread > 0" class="tab-btn mark-all" @click="markAllRead">
        全部已读
      </button>
    </div>

    <!-- Message list -->
    <div class="mail-body">
      <div v-if="loading && messages.length === 0" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <div v-else-if="filteredMessages.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <h3>暂无消息</h3>
        <p>{{ activeTab === 'system' ? '没有系统通知' : activeTab === 'friend' ? '没有好友消息' : '信箱空空如也' }}</p>
      </div>

      <div v-else class="message-list">
        <div
          v-for="msg in filteredMessages"
          :key="msg.id"
          :class="['message-card', { unread: !msg.is_read, selected: selectedMsg?.id === msg.id }]"
          @click="openMessage(msg)"
        >
          <div class="msg-indicator" :class="msg.category"></div>
          <div class="msg-body">
            <div class="msg-top">
              <span class="msg-sender">{{ msg.category === 'system' ? '📢 系统通知' : `👤 ${msg.sender}` }}</span>
              <span class="msg-time">{{ formatTime(msg.created_at) }}</span>
            </div>
            <div class="msg-title">{{ msg.title }}</div>
            <div class="msg-preview">{{ (msg.content || '').slice(0, 60) }}{{ (msg.content || '').length > 60 ? '...' : '' }}</div>
          </div>
          <button class="delete-btn" @click.stop="deleteMessage(msg)">×</button>
        </div>
      </div>
    </div>

    <!-- Message detail -->
    <Teleport to="body">
      <Transition name="slide">
        <div v-if="selectedMsg" class="detail-overlay" @click.self="closeMessage">
          <div class="detail-panel">
            <header class="detail-header">
              <div>
                <span class="detail-cat" :class="selectedMsg.category">{{ categoryLabel(selectedMsg.category) }}</span>
                <h2>{{ selectedMsg.title }}</h2>
              </div>
              <button class="close-btn" @click="closeMessage">×</button>
            </header>
            <div class="detail-meta">
              <span>来自: {{ selectedMsg.category === 'system' ? '系统' : selectedMsg.sender }}</span>
              <span>{{ selectedMsg.created_at }}</span>
            </div>
            <div class="detail-content">{{ selectedMsg.content }}</div>
            <footer class="detail-footer">
              <SpaceButton v-if="selectedMsg.category === 'friend'" variant="primary" size="sm"
                @click="showCompose = true; composeForm.receiver = selectedMsg.sender; composeForm.title = '回复: ' + selectedMsg.title; closeMessage()">
                回复
              </SpaceButton>
              <SpaceButton variant="secondary" size="sm" @click="deleteMessage(selectedMsg)">删除</SpaceButton>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Compose modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showCompose" class="compose-overlay" @click.self="showCompose = false">
          <div class="compose-panel">
            <header class="compose-header">
              <h3>发送消息</h3>
              <button class="close-btn" @click="showCompose = false">×</button>
            </header>

            <div class="compose-body">
              <div class="form-group">
                <label>收件人</label>
                <input v-model="composeForm.receiver" type="text" placeholder="输入用户名" />
                <div v-if="friends.length > 0" class="friend-chips">
                  <button
                    v-for="f in friends.slice(0, 8)"
                    :key="f.id"
                    :class="['chip', { active: composeForm.receiver === f.friend_username }]"
                    @click="selectFriend(f)"
                  >
                    {{ f.friend_username }}
                  </button>
                </div>
              </div>

              <div class="form-group">
                <label>标题</label>
                <input v-model="composeForm.title" type="text" placeholder="消息标题" maxlength="100" />
              </div>

              <div class="form-group">
                <label>内容</label>
                <textarea v-model="composeForm.content" placeholder="写下你的消息..." rows="4" maxlength="500"></textarea>
              </div>
            </div>

            <footer class="compose-footer">
              <SpaceButton variant="secondary" @click="showCompose = false">取消</SpaceButton>
              <SpaceButton variant="primary" :disabled="composeSending" @click="sendCompose">
                {{ composeSending ? '发送中...' : '发送' }}
              </SpaceButton>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.mail-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #0a0f1a 100%);
  padding: 20px;
  padding-bottom: 100px;
  color: #eef7ff;
}

.mail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(180deg, rgba(16, 34, 74, 0.95), rgba(8, 16, 36, 0.96));
  border: 1.5px solid rgba(129, 214, 255, 0.34);
  border-radius: 20px;
  margin-bottom: 16px;
  box-shadow: 0 12px 40px rgba(4, 8, 22, 0.5);
  backdrop-filter: blur(18px);
}

.back-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #dbeeff;
  padding: 8px 16px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
}

h1 { margin: 0; font-size: 22px; flex: 1; text-shadow: 0 0 18px rgba(0, 255, 255, 0.16); }

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.unread-badge {
  background: linear-gradient(135deg, #ff6b9d, #ff4040);
  color: white;
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 99px;
  min-width: 22px;
  text-align: center;
}

/* Tabs */
.tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab-btn {
  flex: 1;
  padding: 12px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(115, 224, 255, 0.12);
  border-radius: 14px;
  color: rgba(222, 240, 255, 0.7);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.tab-btn.active {
  background: linear-gradient(180deg, rgba(49, 120, 255, 0.3), rgba(18, 35, 78, 0.9));
  border-color: rgba(115, 224, 255, 0.4);
  color: #eef7ff;
}

.tab-icon { margin-right: 6px; }

.mark-all {
  flex: 0;
  padding: 12px 16px;
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.3);
  color: #93c5fd;
  font-size: 13px;
  white-space: nowrap;
}

/* Message list */
.message-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(115, 224, 255, 0.08);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.message-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(115, 224, 255, 0.2);
}

.message-card.unread {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.2);
}

.message-card.selected {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
}

.msg-indicator {
  width: 4px;
  height: 40px;
  border-radius: 4px;
  flex-shrink: 0;
}

.msg-indicator.system { background: linear-gradient(180deg, #fbbf24, #f59e0b); }
.msg-indicator.friend { background: linear-gradient(180deg, #60a5fa, #3b82f6); }

.msg-body { flex: 1; min-width: 0; }

.msg-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.msg-sender {
  font-size: 13px;
  color: rgba(222, 240, 255, 0.8);
  font-weight: 600;
}

.msg-time {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.4);
}

.msg-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.message-card.unread .msg-title {
  color: #eef7ff;
}

.msg-preview {
  font-size: 13px;
  color: rgba(222, 240, 255, 0.5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-btn {
  width: 28px;
  height: 28px;
  background: rgba(255, 100, 100, 0.1);
  border: none;
  border-radius: 8px;
  color: rgba(255, 150, 150, 0.6);
  font-size: 18px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.message-card:hover .delete-btn { opacity: 1; }
.delete-btn:hover { background: rgba(255, 100, 100, 0.2); color: #ff6b6b; }

/* States */
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.spinner {
  width: 40px; height: 40px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-icon { font-size: 56px; margin-bottom: 12px; }
.empty-state h3 { margin: 0 0 8px; color: #eef7ff; }
.empty-state p { margin: 0; color: rgba(222, 240, 255, 0.5); }

/* Detail overlay */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.75);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.detail-panel {
  width: 100%;
  max-width: 520px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0f172a, #1e293b);
  border: 1.5px solid rgba(129, 214, 255, 0.34);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 24px 16px;
  border-bottom: 1px solid rgba(115, 224, 255, 0.1);
}

.detail-header h2 { margin: 8px 0 0; font-size: 18px; }

.detail-cat {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.detail-cat.system { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
.detail-cat.friend { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }

.close-btn {
  width: 32px; height: 32px;
  background: rgba(255, 255, 255, 0.05);
  border: none;
  border-radius: 8px;
  color: rgba(222, 240, 255, 0.7);
  font-size: 20px;
  cursor: pointer;
}

.close-btn:hover { background: rgba(255, 255, 255, 0.1); }

.detail-meta {
  display: flex;
  justify-content: space-between;
  padding: 12px 24px;
  font-size: 13px;
  color: rgba(222, 240, 255, 0.5);
}

.detail-content {
  flex: 1;
  padding: 16px 24px;
  font-size: 15px;
  line-height: 1.7;
  color: rgba(238, 247, 255, 0.9);
  white-space: pre-wrap;
  overflow-y: auto;
}

.detail-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid rgba(115, 224, 255, 0.1);
}

/* Compose modal */
.compose-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.75);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1001;
  padding: 20px;
}

.compose-panel {
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0f172a, #1e293b);
  border: 1.5px solid rgba(129, 214, 255, 0.34);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);
}

.compose-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(115, 224, 255, 0.1);
}

.compose-header h3 { margin: 0; font-size: 16px; }

.compose-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.form-group { display: flex; flex-direction: column; gap: 6px; }

.form-group label {
  font-size: 13px;
  color: rgba(222, 240, 255, 0.6);
}

.form-group input, .form-group textarea {
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 12px;
  color: #eef7ff;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.form-group input:focus, .form-group textarea:focus {
  outline: none;
  border-color: rgba(115, 224, 255, 0.4);
}

.friend-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.chip {
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 20px;
  color: rgba(222, 240, 255, 0.7);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.chip:hover { background: rgba(255, 255, 255, 0.1); }

.chip.active {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.4);
  color: #93c5fd;
}

.compose-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid rgba(115, 224, 255, 0.1);
}

/* Transitions */
.slide-enter-active, .slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; }
.slide-enter-from .detail-panel, .slide-leave-to .detail-panel { transform: scale(0.95); }

.modal-enter-active, .modal-leave-active { transition: all 0.25s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .compose-panel, .modal-leave-to .compose-panel { transform: scale(0.95); }
</style>
