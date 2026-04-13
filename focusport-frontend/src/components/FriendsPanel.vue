<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { friendApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const friends = ref([])
const pendingRequests = ref([])
const isLoading = ref(false)
const showAddFriend = ref(false)
const newFriendName = ref('')

const loadFriends = async () => {
  isLoading.value = true
  try {
    const res = await friendApi.list(userStore.username)
    friends.value = res.data.friends?.filter(f => f.status === 'accepted') || []
    pendingRequests.value = res.data.friends?.filter(f => f.status === 'pending') || []
  } catch (error) {
    console.error('加载好友失败:', error)
  } finally {
    isLoading.value = false
  }
}

const sendRequest = async () => {
  if (!newFriendName.value.trim()) return
  try {
    await friendApi.request(userStore.username, newFriendName.value.trim())
    newFriendName.value = ''
    showAddFriend.value = false
    alert('好友请求已发送！')
  } catch (error) {
    alert('发送失败: ' + (error.response?.data?.detail || error.message))
  }
}

const goBack = () => router.push('/')

onMounted(() => loadFriends())
</script>

<template>
  <div class="friends-container">
    <div class="friends-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>👥 星港社区</h1>
      <button class="add-btn" @click="showAddFriend = true">+ 添加</button>
    </div>

    <!-- 待处理请求 -->
    <div v-if="pendingRequests.length > 0" class="section">
      <h3>待处理请求 ({{ pendingRequests.length }})</h3>
      <div class="friend-list">
        <div v-for="req in pendingRequests" :key="req.id" class="friend-item pending">
          <span class="friend-avatar">👤</span>
          <span class="friend-name">{{ req.friend_username }}</span>
          <div class="friend-actions">
            <button class="accept-btn">接受</button>
            <button class="reject-btn">拒绝</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 好友列表 -->
    <div class="section">
      <h3>星港成员 ({{ friends.length }})</h3>
      <div class="friend-list">
        <div v-for="friend in friends" :key="friend.id" class="friend-item">
          <span class="friend-avatar">👤</span>
          <div class="friend-info">
            <span class="friend-name">{{ friend.friend_username }}</span>
            <span class="friend-status">在线</span>
          </div>
          <div class="friend-actions">
            <button class="action-btn">💬</button>
            <button class="action-btn">⚔️</button>
          </div>
        </div>
        <div v-if="friends.length === 0" class="empty-state">
          还没有好友，快去添加吧！
        </div>
      </div>
    </div>

    <!-- 添加好友弹窗 -->
    <div v-if="showAddFriend" class="modal-overlay" @click.self="showAddFriend = false">
      <div class="modal-content">
        <h3>添加联络成员</h3>
        <input
          v-model="newFriendName"
          type="text"
          placeholder="输入用户名"
          @keyup.enter="sendRequest"
        />
        <div class="modal-actions">
          <button @click="showAddFriend = false">取消</button>
          <button class="primary" @click="sendRequest">发送请求</button>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.friends-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  color: white;
}

.friends-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  margin-bottom: 20px;
}

.back-btn, .add-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
}

.add-btn {
  background: rgba(74, 222, 128, 0.25);
  border-color: rgba(74, 222, 128, 0.4);
}

h1 { margin: 0; font-size: 24px; }

.section {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 20px;
  margin-bottom: 16px;
}

.section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
}

.friend-list { display: flex; flex-direction: column; gap: 12px; }

.friend-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 14px;
}

.friend-item.pending {
  background: rgba(251, 191, 36, 0.15);
}

.friend-avatar {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  font-size: 20px;
}

.friend-info { flex: 1; }
.friend-name { display: block; font-weight: 500; }
.friend-status { font-size: 12px; color: #4ade80; }

.friend-actions { display: flex; gap: 8px; }
.action-btn, .accept-btn, .reject-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.accept-btn { background: rgba(74, 222, 128, 0.3); }
.reject-btn { background: rgba(248, 113, 113, 0.3); }

.empty-state {
  text-align: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.5);
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
  border-radius: 20px;
  padding: 24px;
  width: 320px;
}

.modal-content h3 { margin: 0 0 16px 0; }

.modal-content input {
  width: 100%;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  color: white;
  font-size: 15px;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.modal-actions button {
  flex: 1;
  padding: 12px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  font-size: 14px;
}

.modal-actions button.primary {
  background: rgba(74, 222, 128, 0.3);
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
  border-top-color: #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
