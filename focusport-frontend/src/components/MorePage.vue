<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useDimensionStore } from '../stores/dimension'
import SpaceButton from './base/SpaceButton.vue'
import AvatarSelector from './base/AvatarSelector.vue'
import NotificationSettings from './NotificationSettings.vue'
import axios from 'axios'

const router = useRouter()
const userStore = useUserStore()
const dimensionStore = useDimensionStore()

const userAvatar = ref(userStore.avatar || '👤')
const userNickname = ref(userStore.username || '')
const userLevel = ref(1)
const userExp = ref(0)
const showAvatarSelector = ref(false)
const showProfileEditor = ref(false)
const showNotificationSettings = ref(false)
const showPasswordModal = ref(false)

const profileForm = ref({ nickname: '', bio: '' })
const profileLoading = ref(false)

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const passwordLoading = ref(false)
const passwordError = ref('')

const loadUserData = async () => {
  try {
    const growthRes = await axios.get(`/api/growth/${userStore.username}`)
    if (growthRes.data) {
      userLevel.value = growthRes.data.level || 1
      userExp.value = growthRes.data.exp || 0
    }

    const avatarRes = await axios.get(`/api/user/${userStore.username}/avatar`)
    if (avatarRes.data.avatar) {
      userAvatar.value = avatarRes.data.avatar
      userStore.avatar = avatarRes.data.avatar
    }
    if (avatarRes.data.nickname) {
      userNickname.value = avatarRes.data.nickname
    }
  } catch (err) {
    console.error('加载用户数据失败:', err)
  }
}

const levelTitle = computed(() => {
  const level = userLevel.value
  if (level >= 50) return '传奇宇航员'
  if (level >= 40) return '星际探险家'
  if (level >= 30) return '太空先锋'
  if (level >= 20) return '航天员'
  if (level >= 10) return '飞行员'
  return '太空学徒'
})

const expProgress = computed(() => {
  const currentLevelExp = userLevel.value * 100
  const nextLevelExp = (userLevel.value + 1) * 100
  return Math.max(0, ((userExp.value - currentLevelExp) / (nextLevelExp - currentLevelExp)) * 100)
})

const mapWorldEntries = [
  { code: 'PHYSICAL', label: '物理世界', mode: '3D' },
  { code: 'GAIA', label: '盖亚拓扑', mode: '2D' }
]

const settings = computed(() => [
  { icon: '⏳', title: '自律中枢', desc: '进入番茄钟、今日任务与倒数日面板', action: () => router.push('/focus-hub') },
  { icon: '👤', title: '个人资料', desc: '修改头像和昵称', action: openProfileEditor },
  { icon: '🔔', title: '通知设置', desc: '管理推送与提醒', action: () => { showNotificationSettings.value = true } },
  { icon: '🔐', title: '隐私安全', desc: '修改密码与账号安全', action: openPasswordModal },
  { icon: '📊', title: '数据仪表', desc: '查看学习数据概览', action: () => router.push('/dashboard') },
  { icon: '🏆', title: '成就墙', desc: '查看已解锁成就', action: () => router.push('/achievements') },
  { icon: '🛠', title: '开发者设置', desc: '进入后台管理面板', action: () => router.push('/admin') },
  { icon: '📱', title: '关于我们', desc: 'FocusPort v2.0.0', action: () => alert('FocusPort 专注星港 - 让学习更有趣！') }
])

function goBack() {
  router.push('/')
}

function openMapWorld(code) {
  const targetDimension = code === 'PHYSICAL' ? 'PHYSICAL' : 'GAIA'
  dimensionStore.setDimension(targetDimension, userStore.username)
  router.push({
    path: '/island',
    query: { dimension: targetDimension }
  })
}

function logout() {
  if (confirm('确定要退出登录吗？')) {
    userStore.logout()
    router.push('/login')
  }
}

async function onAvatarSelect(avatar) {
  userAvatar.value = avatar
  userStore.avatar = avatar
  try {
    await axios.post(`/api/user/${userStore.username}/avatar`, { avatar })
  } catch (err) {
    console.error('保存头像失败:', err)
  }
}

function openProfileEditor() {
  profileForm.value = {
    nickname: userNickname.value,
    bio: ''
  }
  showProfileEditor.value = true
}

async function saveProfile() {
  profileLoading.value = true
  try {
    await axios.post(`/api/user/${userStore.username}/profile`, {
      nickname: profileForm.value.nickname,
      bio: profileForm.value.bio
    })
    userNickname.value = profileForm.value.nickname
    alert('保存成功！')
    showProfileEditor.value = false
  } catch (err) {
    alert(err.response?.data?.detail || '保存失败')
  } finally {
    profileLoading.value = false
  }
}

function openPasswordModal() {
  passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  passwordError.value = ''
  showPasswordModal.value = true
}

async function changePassword() {
  passwordError.value = ''

  if (!passwordForm.value.oldPassword || !passwordForm.value.newPassword || !passwordForm.value.confirmPassword) {
    passwordError.value = '请填写所有字段'
    return
  }
  if (passwordForm.value.newPassword.length < 6) {
    passwordError.value = '新密码至少需要 6 个字符'
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }

  passwordLoading.value = true
  try {
    await axios.post('/api/change-password', {
      username: userStore.username,
      old_password: passwordForm.value.oldPassword,
      new_password: passwordForm.value.newPassword
    })
    alert('密码修改成功！')
    showPasswordModal.value = false
  } catch (err) {
    passwordError.value = err.response?.data?.detail || '密码修改失败'
  } finally {
    passwordLoading.value = false
  }
}

onMounted(loadUserData)
</script>

<template>
  <div class="more-page space-theme">
    <div class="stars-bg"></div>

    <div class="space-header">
      <SpaceButton variant="secondary" size="sm" @click="goBack">返回</SpaceButton>
      <h1>舰桥中控</h1>
    </div>

    <div class="user-card">
      <div class="user-avatar-wrapper" @click="showAvatarSelector = true">
        <div class="user-avatar">{{ userAvatar }}</div>
        <div class="avatar-edit-hint">更换</div>
      </div>
      <div class="user-info">
        <div class="username">{{ userNickname || userStore.username }}</div>
        <div class="user-level">
          <span class="level-badge">Lv.{{ userLevel }}</span>
          <span class="level-title">{{ levelTitle }}</span>
        </div>
        <div class="exp-bar">
          <div class="exp-fill" :style="{ width: Math.min(expProgress, 100) + '%' }"></div>
          <span class="exp-text">{{ userExp }} EXP</span>
        </div>
      </div>
    </div>

    <div class="map-entry-panel">
      <div class="list-header">我的地图</div>
      <div class="map-entry-stack">
        <button
          v-for="entry in mapWorldEntries"
          :key="entry.code"
          type="button"
          class="map-entry-item"
          :class="{ active: dimensionStore.activeDimension === entry.code }"
          @click="openMapWorld(entry.code)"
        >
          <span class="map-entry-glyph" aria-hidden="true"></span>
          <span class="map-entry-text">{{ entry.label }} ({{ entry.mode }})</span>
        </button>
      </div>
    </div>

    <div class="settings-list">
      <div class="list-header">系统设置</div>
      <div
        v-for="item in settings"
        :key="item.title"
        class="setting-item"
        @click="item.action"
      >
        <span class="setting-icon">{{ item.icon }}</span>
        <div class="setting-content">
          <div class="setting-title">{{ item.title }}</div>
          <div class="setting-desc">{{ item.desc }}</div>
        </div>
        <span class="setting-arrow">→</span>
      </div>
    </div>

    <SpaceButton variant="danger" class="logout-btn" @click="logout">
      退出登录
    </SpaceButton>

    <AvatarSelector
      v-model:visible="showAvatarSelector"
      v-model="userAvatar"
      @select="onAvatarSelect"
    />

    <div v-if="showProfileEditor" class="modal-overlay" @click.self="showProfileEditor = false">
      <div class="profile-modal">
        <div class="modal-header">
          <h3>个人资料</h3>
          <button class="close-btn" @click="showProfileEditor = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>昵称</label>
            <input
              v-model="profileForm.nickname"
              type="text"
              class="form-input"
              placeholder="请输入昵称"
              maxlength="20"
            />
          </div>
          <div class="form-group">
            <label>个人简介</label>
            <textarea
              v-model="profileForm.bio"
              class="form-input bio-input"
              placeholder="介绍一下自己（可选）"
              maxlength="200"
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <SpaceButton variant="secondary" @click="showProfileEditor = false">取消</SpaceButton>
          <SpaceButton variant="primary" :loading="profileLoading" @click="saveProfile">保存</SpaceButton>
        </div>
      </div>
    </div>

    <div v-if="showNotificationSettings" class="modal-overlay" @click.self="showNotificationSettings = false">
      <div class="notification-modal">
        <div class="modal-header">
          <h3>通知设置</h3>
          <button class="close-btn" @click="showNotificationSettings = false">×</button>
        </div>
        <div class="modal-body">
          <NotificationSettings />
        </div>
        <div class="modal-footer">
          <SpaceButton variant="primary" @click="showNotificationSettings = false">完成</SpaceButton>
        </div>
      </div>
    </div>

    <div v-if="showPasswordModal" class="modal-overlay" @click.self="showPasswordModal = false">
      <div class="password-modal">
        <div class="modal-header">
          <h3>修改密码</h3>
          <button class="close-btn" @click="showPasswordModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>原密码</label>
            <input v-model="passwordForm.oldPassword" type="password" class="form-input" placeholder="请输入原密码" />
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input v-model="passwordForm.newPassword" type="password" class="form-input" placeholder="至少 6 个字符" />
          </div>
          <div class="form-group">
            <label>确认新密码</label>
            <input v-model="passwordForm.confirmPassword" type="password" class="form-input" placeholder="再次输入新密码" />
          </div>
          <div v-if="passwordError" class="error-msg">{{ passwordError }}</div>
        </div>
        <div class="modal-footer">
          <SpaceButton variant="secondary" @click="showPasswordModal = false">取消</SpaceButton>
          <SpaceButton variant="primary" :loading="passwordLoading" @click="changePassword">确认修改</SpaceButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.more-page.space-theme {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0f1a 0%, #0f172a 50%, #0a0f1a 100%);
  padding: 20px;
  color: white;
  font-family: 'Segoe UI', sans-serif;
  position: relative;
}

.stars-bg {
  position: fixed;
  inset: 0;
  background-image:
    radial-gradient(2px 2px at 20px 30px, #fff, transparent),
    radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
    radial-gradient(1px 1px at 90px 40px, #fff, transparent),
    radial-gradient(1px 1px at 130px 80px, rgba(255,255,255,0.6), transparent);
  background-size: 200px 120px;
  opacity: 0.35;
  pointer-events: none;
}

.space-header,
.user-card,
.settings-list,
.logout-btn {
  position: relative;
  z-index: 1;
}

.space-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 960px;
  margin: 0 auto 20px;
}

.space-header h1 {
  margin: 0;
  font-size: 34px;
}

.user-card {
  max-width: 960px;
  margin: 0 auto 20px;
  display: flex;
  gap: 20px;
  align-items: center;
  padding: 24px;
  border-radius: 24px;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(18px);
}

.user-avatar-wrapper {
  position: relative;
  cursor: pointer;
}

.user-avatar {
  width: 88px;
  height: 88px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  font-size: 40px;
  background: linear-gradient(135deg, #38bdf8, #818cf8);
}

.avatar-edit-hint {
  margin-top: 8px;
  text-align: center;
  color: #7dd3fc;
  font-size: 13px;
}

.user-info {
  flex: 1;
}

.username {
  font-size: 28px;
  font-weight: 700;
}

.user-level {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 8px;
}

.level-badge {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.2);
  color: #7dd3fc;
}

.level-title {
  color: rgba(255, 255, 255, 0.78);
}

.exp-bar {
  position: relative;
  margin-top: 16px;
  height: 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.exp-fill {
  height: 100%;
  background: linear-gradient(90deg, #38bdf8, #f59e0b);
}

.exp-text {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
}

.map-entry-panel {
  max-width: 960px;
  margin: 0 auto 20px;
  padding: 20px;
  border-radius: 24px;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.map-entry-stack {
  display: grid;
  gap: 12px;
}

.map-entry-item {
  width: 100%;
  min-height: 64px;
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(148, 163, 184, 0.2), rgba(15, 23, 42, 0.35));
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  text-align: left;
  color: #e2e8f0;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.map-entry-item:hover {
  transform: translateY(-1px);
  border-color: rgba(125, 211, 252, 0.65);
}

.map-entry-item.active {
  border-color: rgba(56, 189, 248, 0.9);
  background: linear-gradient(180deg, rgba(56, 189, 248, 0.2), rgba(30, 41, 59, 0.4));
}

.map-entry-glyph {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #0b84ff;
  box-shadow: 0 0 0 4px rgba(11, 132, 255, 0.2);
  flex-shrink: 0;
}

.map-entry-text {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
  color: #7dd3fc;
  letter-spacing: 0.12px;
}

.settings-list {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px;
  border-radius: 24px;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.list-header {
  font-size: 14px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #7dd3fc;
  margin-bottom: 12px;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-icon {
  font-size: 22px;
}

.setting-content {
  flex: 1;
}

.setting-title {
  font-weight: 700;
}

.setting-desc {
  margin-top: 4px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 14px;
}

.setting-arrow {
  color: #7dd3fc;
}

.logout-btn {
  max-width: 960px;
  margin: 20px auto 0;
  width: 100%;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(2, 6, 23, 0.66);
}

.profile-modal,
.notification-modal,
.password-modal {
  width: min(560px, 100%);
  border-radius: 24px;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.modal-header,
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 18px 20px;
}

.modal-body {
  padding: 0 20px 20px;
}

.close-btn {
  border: none;
  background: transparent;
  color: white;
  font-size: 28px;
  cursor: pointer;
}

.form-group {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}

.form-input {
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: white;
}

.bio-input {
  min-height: 96px;
  resize: vertical;
}

.error-msg {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.14);
  color: #fca5a5;
}

@media (max-width: 768px) {
  .space-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .user-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
