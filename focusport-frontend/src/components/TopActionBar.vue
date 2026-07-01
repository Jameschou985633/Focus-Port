<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const rootRef = ref(null)
const beaconOpen = ref(false)
const avatarOpen = ref(false)

const beaconItems = [
  { id: 'friend', label: '好友请求', dot: true },
  { id: 'system', label: '系统通知', dot: true },
  { id: 'collab', label: '联机邀请', dot: false },
  { id: 'event', label: '活动提醒', dot: false }
]

const unreadCount = computed(() => beaconItems.filter((item) => item.dot).length)
const username = computed(() => userStore.username || 'guest')
const avatarText = computed(() => (username.value?.[0] || 'G').toUpperCase())

const closeAll = () => {
  beaconOpen.value = false
  avatarOpen.value = false
}

const toggleBeacon = () => {
  beaconOpen.value = !beaconOpen.value
  if (beaconOpen.value) avatarOpen.value = false
}

const toggleAvatar = () => {
  avatarOpen.value = !avatarOpen.value
  if (avatarOpen.value) beaconOpen.value = false
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}

const handlePointerDown = (event) => {
  if (!rootRef.value) return
  if (!rootRef.value.contains(event.target)) closeAll()
}

const handleEsc = (event) => {
  if (event.key === 'Escape') closeAll()
}

onMounted(() => {
  window.addEventListener('pointerdown', handlePointerDown)
  window.addEventListener('keydown', handleEsc)
})

onUnmounted(() => {
  window.removeEventListener('pointerdown', handlePointerDown)
  window.removeEventListener('keydown', handleEsc)
})
</script>

<template>
  <header ref="rootRef" class="top-action-bar">
    <button type="button" class="logo-btn" @click="router.push('/')">FocusPort</button>

    <div class="right-controls">
      <div class="dropdown-wrap">
        <button type="button" class="icon-btn" aria-label="星港信标" @click="toggleBeacon">
          🔔
          <span v-if="unreadCount > 0" class="unread">{{ unreadCount }}</span>
        </button>
        <transition name="drop">
          <div v-if="beaconOpen" class="dropdown-panel">
            <p class="panel-title">星港信标 Beacon</p>
            <button v-for="item in beaconItems" :key="item.id" type="button" class="panel-item">
              <span>{{ item.label }}</span>
              <em v-if="item.dot">●</em>
            </button>
            <button type="button" class="panel-link" @click="router.push('/more')">查看全部</button>
          </div>
        </transition>
      </div>

      <div class="dropdown-wrap">
        <button type="button" class="avatar-btn" aria-label="个人中心" @click="toggleAvatar">
          <span class="avatar">{{ avatarText }}</span>
          <span class="name">{{ username }}</span>
        </button>
        <transition name="drop">
          <div v-if="avatarOpen" class="dropdown-panel">
            <button type="button" class="panel-item" @click="router.push('/more')">个人资料</button>
            <button type="button" class="panel-item" @click="router.push('/more')">账号设置</button>
            <button type="button" class="panel-item" @click="router.push('/more')">通知设置</button>
            <button type="button" class="panel-item danger" @click="logout">退出登录</button>
          </div>
        </transition>
      </div>
    </div>
  </header>
</template>

<style scoped>
.top-action-bar {
  position: fixed;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  width: min(1180px, calc(100vw - 24px));
  min-height: 54px;
  border-radius: 16px;
  border: 1px solid rgba(118, 188, 255, 0.26);
  background: rgba(9, 23, 48, 0.8);
  box-shadow: 0 16px 30px rgba(3, 9, 20, 0.4);
  backdrop-filter: blur(14px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
}

.logo-btn {
  border: 0;
  background: transparent;
  color: #9fd0ff;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.01em;
  cursor: pointer;
}

.right-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dropdown-wrap {
  position: relative;
}

.icon-btn,
.avatar-btn {
  min-height: 38px;
  border-radius: 10px;
  border: 1px solid rgba(126, 185, 255, 0.35);
  background: rgba(20, 40, 73, 0.8);
  color: #d8ecff;
  cursor: pointer;
}

.icon-btn {
  position: relative;
  min-width: 38px;
}

.unread {
  position: absolute;
  top: -7px;
  right: -6px;
  min-width: 18px;
  min-height: 18px;
  border-radius: 999px;
  background: #1f9fff;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  box-shadow: 0 0 14px rgba(31, 159, 255, 0.5);
}

.avatar-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px 0 8px;
}

.avatar {
  width: 22px;
  height: 22px;
  border-radius: 8px;
  background: rgba(50, 118, 222, 0.5);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.name {
  font-size: 12px;
}

.dropdown-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 10px);
  width: 220px;
  border-radius: 14px;
  border: 1px solid rgba(126, 180, 255, 0.28);
  background: rgba(8, 19, 38, 0.95);
  backdrop-filter: blur(14px);
  box-shadow: 0 20px 32px rgba(5, 14, 30, 0.48);
  padding: 10px;
}

.panel-title {
  margin: 2px 6px 8px;
  font-size: 12px;
  color: #9fc9fb;
}

.panel-item,
.panel-link {
  width: 100%;
  min-height: 34px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #d8ecff;
  text-align: left;
  padding: 0 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-item:hover,
.panel-link:hover {
  background: rgba(65, 124, 220, 0.2);
}

.panel-item em {
  font-style: normal;
  color: #39b7ff;
}

.panel-link {
  color: #96c1f6;
}

.panel-item.danger {
  color: #ff9fb1;
}

.drop-enter-active,
.drop-leave-active {
  transition: all 200ms ease-out;
}

.drop-enter-from,
.drop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}

@media (max-width: 768px) {
  .top-action-bar {
    width: calc(100vw - 14px);
    top: 8px;
  }

  .logo-btn {
    font-size: 19px;
  }

  .name {
    max-width: 58px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
