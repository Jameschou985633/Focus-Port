<template>
  <main class="vision-login-shell">
    <section class="vision-login-frame" aria-label="FocusPort 登录界面">
      <aside class="vision-hero" aria-label="FocusPort 视觉看板">
        <div class="hero-glass hero-glass-top"></div>
        <div class="hero-glass hero-glass-bottom"></div>

        <div class="hero-copy">
          <p class="hero-kicker">降噪，拆解，跃迁</p>
          <p class="hero-eyebrow">INSPIRED BY FOCUS:</p>
          <h1>THE FOCUSPORT DASHBOARD</h1>
          <p class="hero-system">FOCUS HUB OS // SYSTEM BOOTING</p>
        </div>
      </aside>

      <section class="vision-auth-panel">
        <div class="auth-orbit auth-orbit-one"></div>
        <div class="auth-orbit auth-orbit-two"></div>

        <div class="auth-card">
          <div class="auth-heading">
            <p class="auth-kicker">LOGIN PROTOCOL</p>
            <h2>身份核验：星港指挥官</h2>
            <p>
              {{ isLogin ? '输入序列号与密钥，进入今日专注舱。' : '建立新的指挥官档案，开启你的 FocusPort 航线。' }}
            </p>
          </div>

          <div class="auth-tabs" role="tablist" aria-label="登录或注册">
            <button
              type="button"
              :class="['auth-tab', { active: isLogin }]"
              role="tab"
              :aria-selected="isLogin"
              @click="switchMode(true)"
            >
              登录
            </button>
            <button
              type="button"
              :class="['auth-tab', { active: !isLogin }]"
              role="tab"
              :aria-selected="!isLogin"
              @click="switchMode(false)"
            >
              建档
            </button>
          </div>

          <form class="auth-form" @submit.prevent="handleSubmit">
            <label class="field-group">
              <span>指挥官序列号</span>
              <input
                v-model.trim="username"
                type="text"
                autocomplete="username"
                placeholder="输入邮箱或用户名"
              />
            </label>

            <label class="field-group">
              <span>降噪密钥</span>
              <input
                v-model="password"
                type="password"
                :autocomplete="isLogin ? 'current-password' : 'new-password'"
                placeholder="输入你的登录密钥"
              />
            </label>

            <label v-if="!isLogin" class="field-group">
              <span>再次确认密钥</span>
              <input
                v-model="confirmPassword"
                type="password"
                autocomplete="new-password"
                placeholder="再次输入密钥"
              />
            </label>

            <div class="auth-options">
              <button
                class="remember-toggle"
                type="button"
                :aria-pressed="rememberSession"
                @click="rememberSession = !rememberSession"
              >
                <span :class="['toggle-track', { active: rememberSession }]">
                  <span class="toggle-dot"></span>
                </span>
                <span>保持神经连接</span>
              </button>
              <span class="status-link">安全通道已加密</span>
            </div>

            <p v-if="errorMsg" class="form-message error" role="alert">{{ errorMsg }}</p>
            <p v-else-if="successMsg" class="form-message success" role="status">{{ successMsg }}</p>

            <button class="primary-button" type="submit" :disabled="isLoading">
              <span>{{ buttonText }}</span>
              <span class="button-arrow">→</span>
            </button>
          </form>

          <button class="mode-switch" type="button" @click="switchMode(!isLogin)">
            {{ isLogin ? '未收录生物特征？申请建立新建档' : '已有指挥官档案？返回身份核验' }}
          </button>
        </div>
      </section>
    </section>

    <LoginTransitionOverlay
      :show="showLoginTransition"
      :username="username"
      @complete="onTransitionComplete"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
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
const successMsg = ref('')
const showLoginTransition = ref(false)
const rememberSession = ref(true)

const buttonText = computed(() => {
  if (isLoading.value) {
    return isLogin.value ? '协议启动中...' : '建档中...'
  }

  return isLogin.value ? '启动跃迁协议' : '建立新建档'
})

const switchMode = (loginMode: boolean) => {
  isLogin.value = loginMode
  errorMsg.value = ''
  successMsg.value = ''
  confirmPassword.value = ''
}

const handleSubmit = async () => {
  errorMsg.value = ''
  successMsg.value = ''

  if (!username.value || !password.value) {
    errorMsg.value = '请填写指挥官序列号和降噪密钥。'
    return
  }

  if (!isLogin.value && password.value !== confirmPassword.value) {
    errorMsg.value = '两次输入的密钥不一致，请重新确认。'
    return
  }

  isLoading.value = true

  try {
    if (isLogin.value) {
      const response = await authApi.login(username.value, password.value)
      if (response.data.success) {
        localStorage.setItem('username', username.value)
        userStore.username = username.value
        await userStore.loadGrowth()
        showLoginTransition.value = true
      } else {
        errorMsg.value = response.data.message || '身份核验失败，请检查序列号或密钥。'
      }
    } else {
      const response = await authApi.register(username.value, password.value)
      if (response.data.success) {
        successMsg.value = '建档成功，请使用你的指挥官序列号登录。'
        isLogin.value = true
        password.value = ''
        confirmPassword.value = ''
      } else {
        errorMsg.value = response.data.message || '建档失败，请稍后再试。'
      }
    }
  } catch (error: any) {
    errorMsg.value = error.response?.data?.detail || error.response?.data?.message || '网络异常，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

const onTransitionComplete = () => {
  router.push('/')
}
</script>

<style scoped>
.vision-login-shell {
  position: relative;
  min-height: 100vh;
  width: 100%;
  overflow: hidden;
  color: #f7fbff;
  background:
    radial-gradient(circle at 18% 12%, rgba(72, 128, 255, 0.28), transparent 28%),
    radial-gradient(circle at 82% 78%, rgba(41, 217, 255, 0.16), transparent 30%),
    linear-gradient(135deg, #050817 0%, #080c24 45%, #020411 100%);
  font-family: "Plus Jakarta Sans", "Noto Sans SC", "Microsoft YaHei", sans-serif;
}

.vision-topbar {
  position: absolute;
  top: clamp(18px, 3vw, 38px);
  left: clamp(18px, 4vw, 64px);
  right: clamp(18px, 4vw, 64px);
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  pointer-events: none;
}

.brand-chip,
.nav-action,
.auth-tab,
.remember-toggle,
.mode-switch,
.primary-button {
  border: 0;
  font: inherit;
}

.brand-chip,
.nav-action {
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: #ffffff;
  background: rgba(9, 14, 39, 0.58);
  border: 1px solid rgba(255, 255, 255, 0.13);
  box-shadow: 0 18px 46px rgba(0, 0, 0, 0.24);
  backdrop-filter: blur(18px);
}

.brand-chip {
  padding: 10px 16px 10px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-mark {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  color: #06102a;
  background: linear-gradient(135deg, #d8f8ff, #4880ff 62%, #8bb0ff);
  font-size: 12px;
  font-weight: 900;
}

.nav-pills {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(6, 10, 31, 0.48);
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.22);
  backdrop-filter: blur(18px);
}

.nav-pills span {
  padding: 9px 17px;
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.nav-pills span:first-child {
  color: #ffffff;
  background: rgba(72, 128, 255, 0.24);
}

.nav-action {
  padding: 14px 20px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.vision-login-frame {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(430px, 0.92fr);
  isolation: isolate;
}

.vision-hero {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    linear-gradient(90deg, rgba(4, 7, 20, 0.38), rgba(4, 7, 20, 0.05) 48%, rgba(4, 7, 20, 0.68)),
    linear-gradient(180deg, rgba(4, 7, 20, 0.16), rgba(4, 7, 20, 0.55)),
    url('/assets/login-vision-bg.png') center / cover no-repeat,
    radial-gradient(circle at 35% 35%, rgba(73, 129, 255, 0.5), transparent 30%),
    linear-gradient(135deg, #1b245a, #090c23 72%);
}

.vision-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.82), transparent 78%);
  opacity: 0.52;
}

.vision-hero::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(4, 7, 20, 0.18) 60%, #070b22 100%);
}

.hero-glass {
  position: absolute;
  z-index: 1;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 28px;
  background: rgba(5, 10, 32, 0.36);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(20px);
}

.hero-glass-top {
  top: 16%;
  left: 8%;
  width: min(34vw, 430px);
  height: 118px;
  opacity: 0.82;
}

.hero-glass-bottom {
  right: 9%;
  bottom: 14%;
  width: min(28vw, 350px);
  height: 156px;
  opacity: 0.7;
}

.hero-copy {
  position: absolute;
  left: clamp(30px, 6vw, 96px);
  bottom: clamp(42px, 10vh, 128px);
  z-index: 2;
  max-width: 680px;
}

.hero-kicker {
  margin: 0 0 30px;
  color: rgba(255, 255, 255, 0.86);
  font-size: clamp(22px, 2.2vw, 34px);
  font-weight: 800;
  letter-spacing: 0.08em;
}

.hero-eyebrow,
.hero-system,
.auth-kicker {
  margin: 0;
  color: rgba(215, 226, 255, 0.66);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.hero-copy h1 {
  margin: 12px 0 26px;
  color: #ffffff;
  font-size: clamp(42px, 6vw, 96px);
  line-height: 0.94;
  font-weight: 950;
  letter-spacing: -0.07em;
  text-shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
}

.hero-system {
  color: rgba(255, 255, 255, 0.56);
}

.vision-auth-panel {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: clamp(96px, 12vh, 148px) clamp(34px, 6vw, 94px) 46px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(10, 16, 48, 0.94), rgba(4, 7, 22, 0.98)),
    radial-gradient(circle at 14% 20%, rgba(72, 128, 255, 0.2), transparent 28%);
}

.vision-auth-panel::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.18;
}

.auth-orbit {
  position: absolute;
  border-radius: 50%;
  filter: blur(6px);
  opacity: 0.36;
}

.auth-orbit-one {
  top: 18%;
  right: -70px;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(72, 128, 255, 0.58), transparent 68%);
}

.auth-orbit-two {
  bottom: 10%;
  left: -90px;
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(36, 211, 255, 0.45), transparent 68%);
}

.auth-card {
  position: relative;
  z-index: 1;
  width: min(100%, 520px);
  margin: 0 auto;
}

.auth-heading h2 {
  margin: 14px 0 12px;
  color: #ffffff;
  font-size: clamp(30px, 3vw, 45px);
  line-height: 1.05;
  font-weight: 900;
  letter-spacing: -0.04em;
}

.auth-heading p:last-child {
  margin: 0;
  max-width: 420px;
  color: rgba(220, 230, 255, 0.68);
  font-size: 15px;
  line-height: 1.8;
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 34px 0 26px;
  padding: 7px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.055);
}

.auth-tab {
  min-height: 42px;
  border-radius: 999px;
  color: rgba(232, 240, 255, 0.66);
  background: transparent;
  font-weight: 900;
  letter-spacing: 0.12em;
  cursor: pointer;
  transition: 0.22s ease;
}

.auth-tab.active {
  color: #071029;
  background: linear-gradient(135deg, #ffffff 0%, #dce8ff 100%);
  box-shadow: 0 12px 30px rgba(72, 128, 255, 0.24);
}

.auth-form {
  display: grid;
  gap: 18px;
}

.field-group {
  display: grid;
  gap: 10px;
}

.field-group span {
  color: rgba(238, 244, 255, 0.82);
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.1em;
}

.field-group input {
  width: 100%;
  height: 56px;
  padding: 0 19px;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.11);
  border-radius: 20px;
  outline: none;
  background: rgba(255, 255, 255, 0.075);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 16px 36px rgba(0, 0, 0, 0.14);
  font-size: 15px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.field-group input::placeholder {
  color: rgba(215, 225, 255, 0.38);
}

.field-group input:focus {
  border-color: rgba(72, 128, 255, 0.86);
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 0 4px rgba(72, 128, 255, 0.16), 0 18px 42px rgba(0, 0, 0, 0.18);
}

.auth-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 2px 0 4px;
  color: rgba(220, 230, 255, 0.62);
  font-size: 13px;
}

.remember-toggle {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  background: transparent;
  cursor: pointer;
}

.toggle-track {
  position: relative;
  display: inline-flex;
  width: 38px;
  height: 22px;
  align-items: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  transition: 0.2s ease;
}

.toggle-track.active {
  background: #4880ff;
}

.toggle-dot {
  width: 16px;
  height: 16px;
  margin-left: 3px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 5px 12px rgba(0, 0, 0, 0.25);
  transition: transform 0.2s ease;
}

.toggle-track.active .toggle-dot {
  transform: translateX(16px);
}

.status-link {
  color: rgba(127, 181, 255, 0.86);
  font-weight: 800;
}

.form-message {
  margin: 0;
  padding: 13px 16px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.5;
}

.form-message.error {
  color: #ffd6d6;
  border: 1px solid rgba(255, 104, 104, 0.28);
  background: rgba(255, 75, 75, 0.12);
}

.form-message.success {
  color: #c6ffe2;
  border: 1px solid rgba(73, 231, 155, 0.28);
  background: rgba(73, 231, 155, 0.12);
}

.primary-button {
  display: inline-flex;
  width: 100%;
  min-height: 58px;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 2px;
  color: #ffffff;
  border-radius: 999px;
  background: linear-gradient(135deg, #4880ff 0%, #1c5cff 48%, #28d3ff 100%);
  box-shadow: 0 24px 54px rgba(72, 128, 255, 0.36);
  font-weight: 950;
  letter-spacing: 0.12em;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.primary-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 30px 70px rgba(72, 128, 255, 0.46);
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.button-arrow {
  display: grid;
  width: 27px;
  height: 27px;
  place-items: center;
  border-radius: 50%;
  color: #0d1a45;
  background: rgba(255, 255, 255, 0.88);
  font-size: 18px;
}

.mode-switch {
  display: block;
  width: fit-content;
  margin: 26px auto 0;
  color: rgba(222, 233, 255, 0.72);
  background: transparent;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: color 0.2s ease;
}

.mode-switch:hover {
  color: #ffffff;
}

.auth-footer {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  gap: 28px;
  margin-top: auto;
  padding-top: 46px;
  color: rgba(226, 236, 255, 0.42);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

@media (max-width: 1080px) {
  .vision-login-frame {
    grid-template-columns: minmax(0, 0.95fr) minmax(400px, 1.05fr);
  }

  .nav-pills {
    display: none;
  }
}

@media (max-width: 880px) {
  .vision-login-shell {
    overflow-y: auto;
  }

  .vision-topbar {
    position: fixed;
  }

  .vision-login-frame {
    grid-template-columns: 1fr;
  }

  .vision-hero {
    min-height: 42vh;
  }

  .hero-copy {
    right: 28px;
    bottom: 36px;
  }

  .hero-glass-top,
  .hero-glass-bottom {
    display: none;
  }

  .vision-auth-panel {
    min-height: 58vh;
    padding-top: 54px;
  }

  .auth-card {
    width: min(100%, 560px);
  }
}

@media (max-width: 560px) {
  .vision-topbar {
    top: 14px;
    left: 14px;
    right: 14px;
  }

  .brand-chip {
    padding-right: 12px;
    font-size: 11px;
  }

  .brand-mark {
    width: 30px;
    height: 30px;
  }

  .nav-action {
    padding: 11px 13px;
    font-size: 11px;
  }

  .vision-hero {
    min-height: 38vh;
  }

  .hero-copy {
    left: 22px;
    right: 22px;
    bottom: 28px;
  }

  .hero-kicker {
    margin-bottom: 16px;
    font-size: 18px;
  }

  .hero-copy h1 {
    margin-bottom: 16px;
    font-size: 40px;
  }

  .vision-auth-panel {
    padding: 38px 20px 28px;
  }

  .auth-heading h2 {
    font-size: 30px;
  }

  .auth-options {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .auth-footer {
    gap: 16px;
    flex-wrap: wrap;
    padding-top: 34px;
  }
}
</style>
