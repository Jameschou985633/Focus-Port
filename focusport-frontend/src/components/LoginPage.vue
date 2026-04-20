<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../api'
import { useUserStore } from '../stores/user'
import LoginTransitionOverlay from './LoginTransitionOverlay.vue'

const router = useRouter()
const userStore = useUserStore()

const isLogin = ref(true)
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const errorMsg = ref('')
const showLoginTransition = ref(false)

const handleSubmit = async () => {
  errorMsg.value = ''

  if (!username.value.trim() || !password.value.trim()) {
    errorMsg.value = '请填写用户名和密码'
    return
  }

  if (!isLogin.value && password.value !== confirmPassword.value) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }

  isLoading.value = true

  try {
    if (isLogin.value) {
      const res = await authApi.login(username.value.trim(), password.value)
      if (res.data.success) {
        userStore.username = username.value.trim()
        localStorage.setItem('username', username.value.trim())
        await userStore.loadGrowth()
        showLoginTransition.value = true
      }
    } else {
      const res = await authApi.register(username.value.trim(), password.value)
      if (res.data.success) {
        alert('注册成功，请登录')
        isLogin.value = true
      }
    }
  } catch (error) {
    errorMsg.value = error.response?.data?.detail || (isLogin.value ? '登录失败' : '注册失败')
  } finally {
    isLoading.value = false
  }
}

const onLoginAnimationDone = () => {
  router.push('/')
}

const switchMode = () => {
  isLogin.value = !isLogin.value
  errorMsg.value = ''
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="logo">🚀</div>
        <h1>FocusPort</h1>
        <p>专注星港 · 学习成长平台</p>
      </div>

      <div class="tab-switch">
        <button :class="{ active: isLogin }" @click="isLogin = true">登录</button>
        <button :class="{ active: !isLogin }" @click="isLogin = false">注册</button>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>用户名</label>
          <input
            v-model="username"
            type="text"
            placeholder="请输入用户名"
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label>密码</label>
          <input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            :autocomplete="isLogin ? 'current-password' : 'new-password'"
          />
        </div>

        <div v-if="!isLogin" class="form-group">
          <label>确认密码</label>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            autocomplete="new-password"
          />
        </div>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

        <button type="submit" class="submit-btn" :disabled="isLoading">
          {{ isLoading ? '处理中...' : (isLogin ? '登录' : '注册') }}
        </button>
      </form>

      <div class="login-footer">
        <p @click="switchMode">
          {{ isLogin ? '没有账号？点击注册' : '已有账号？点击登录' }}
        </p>
        <p v-if="isLogin" class="forgot-hint">如需重置密码请联系管理员</p>
      </div>
    </div>

    <div class="features-preview">
      <div class="feature-item">
        <span class="feature-icon">⏱</span>
        <span>专注计时</span>
      </div>
      <div class="feature-item">
        <span class="feature-icon">📝</span>
        <span>语言考核站</span>
      </div>
      <div class="feature-item">
        <span class="feature-icon">🏆</span>
        <span>排行榜</span>
      </div>
      <div class="feature-item">
        <span class="feature-icon">🤖</span>
        <span>AI 助手</span>
      </div>
    </div>
  </div>

  <LoginTransitionOverlay :visible="showLoginTransition" @done="onLoginAnimationDone" />
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #fff;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: rgba(10, 15, 26, 0.86);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 24px;
  padding: 32px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(18px);
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.logo {
  width: 72px;
  height: 72px;
  margin: 0 auto 12px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  font-size: 32px;
  background: linear-gradient(135deg, #38bdf8, #60a5fa);
}

.login-header h1 {
  margin: 0;
  font-size: 30px;
}

.login-header p {
  margin: 8px 0 0;
  color: rgba(255, 255, 255, 0.72);
}

.tab-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 20px;
}

.tab-switch button,
.submit-btn {
  border: none;
  border-radius: 14px;
  cursor: pointer;
  font-weight: 700;
}

.tab-switch button {
  padding: 12px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.74);
}

.tab-switch button.active {
  background: linear-gradient(135deg, #38bdf8, #60a5fa);
  color: #08111e;
}

.login-form {
  display: grid;
  gap: 14px;
}

.form-group {
  display: grid;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.84);
}

.form-group input {
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.form-group input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.submit-btn {
  margin-top: 6px;
  padding: 13px 16px;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #111827;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-msg {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.14);
  color: #fca5a5;
  font-size: 14px;
}

.login-footer {
  margin-top: 18px;
  text-align: center;
}

.login-footer p {
  color: #7dd3fc;
  cursor: pointer;
  margin: 0;
}

.forgot-hint {
  margin-top: 8px !important;
  color: rgba(222, 240, 255, 0.4) !important;
  cursor: default !important;
  font-size: 12px;
}

.features-preview {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
  max-width: 420px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.86);
}

.feature-icon {
  font-size: 18px;
}
</style>
