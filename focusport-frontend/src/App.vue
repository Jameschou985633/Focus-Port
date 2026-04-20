<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BackgroundMusic from './components/BackgroundMusic.vue'
import DimensionTransitionOverlay from './components/DimensionTransitionOverlay.vue'
import { useDimensionStore } from './stores/dimension'
import { useMailStore } from './stores/mail'

const route = useRoute()
const router = useRouter()
const dimensionStore = useDimensionStore()
const mailStore = useMailStore()

const sideMenuOpen = ref(false)
const activeMenuId = ref(null)
const showFloatingMenu = computed(() => route.path !== '/login' && route.path !== '/')

const syncMailPolling = () => {
  const username = localStorage.getItem('username')
  if (username) {
    mailStore.startPolling(username)
    return
  }
  mailStore.stopPolling()
}


const closeSideMenu = () => {
  sideMenuOpen.value = false
  activeMenuId.value = null
}

const toggleSideMenu = () => {
  sideMenuOpen.value = !sideMenuOpen.value
  if (!sideMenuOpen.value) {
    activeMenuId.value = null
  }
}

const goTo = (path) => {
  closeSideMenu()
  router.push(path)
}

const goHome = () => goTo('/')
const goAI = () => goTo('/ai')
const goFleetHub = () => goTo('/collab')
const goGrowth = () => goTo('/stats')
const goPlayground = () => goTo('/playground')
const goShop = () => goTo('/shop')
const goVault = () => goTo('/vault')
const goPlans = () => goTo('/plans')
const goExam = () => goTo('/exam')
const goFriends = () => goTo('/friends')
const goPK = () => goTo('/pk')
const goLeaderboard = () => goTo('/leaderboard')
const goAchievements = () => goTo('/achievements')
const goGomoku = () => goTo('/playground/gomoku-solo')
const goTicTacToe = () => goTo('/playground/tictactoe')
const goConnectFour = () => goTo('/playground/connect-four')
const goMail = () => goTo('/mail')

const activeGlassPreset = ref('aurora')
const glassMotionEnabled = ref(true)

const applyGlassAppearance = () => {
  const root = document.documentElement
  root.dataset.glassPreset = activeGlassPreset.value
  root.classList.toggle('glass-motion-off', !glassMotionEnabled.value)
}

const setGlassPreset = (preset) => {
  activeGlassPreset.value = preset
  applyGlassAppearance()
}

const setGlassMotion = (enabled) => {
  glassMotionEnabled.value = enabled
  applyGlassAppearance()
}

const goWorld3D = () => {
  closeSideMenu()
  dimensionStore.setDimension('PHYSICAL')
  router.push('/island')
}

const goWorld2D = () => {
  closeSideMenu()
  dimensionStore.setDimension('GAIA')
  router.push('/island')
}

const menuItems = [
  {
    id: 'core',
    title: '核心中枢',
    icon: 'core',
    action: goHome
  },
  {
    id: 'world',
    title: '星港世界',
    icon: 'world',
    children: [
      { id: 'world-3d', title: '进入 3D 城市', action: goWorld3D },
      { id: 'world-2d', title: '进入 2D 城市', action: goWorld2D },
      { id: 'world-shop', title: '物质交换港', action: goShop },
      { id: 'world-vault', title: '工程装备仓', action: goVault }
    ]
  },
  {
    id: 'ai',
    title: '智能终端',
    icon: 'ai',
    children: [
      { id: 'ai-terminal', title: 'AI 副官终端', action: goAI },
      { id: 'ai-plan', title: '学习计划', action: goPlans },
      { id: 'ai-exam', title: '语言考核站', action: goExam }
    ]
  },
  {
    id: 'fleet',
    title: '舰队枢纽',
    icon: 'fleet',
    children: [
      { id: 'fleet-bridge', title: '联合星桥', action: goFleetHub },
      { id: 'fleet-friends', title: '星际通讯录', action: goFriends },
      { id: 'fleet-pk', title: '星环竞技场', action: goPK },
      { id: 'fleet-mail', title: '星际信箱', action: goMail }
    ]
  },
  {
    id: 'growth',
    title: '履历档案',
    icon: 'growth',
    children: [
      { id: 'growth-stats', title: '成长统计', action: goGrowth },
      { id: 'growth-rank', title: '排行榜', action: goLeaderboard },
      { id: 'growth-ach', title: '成就墙', action: goAchievements }
    ]
  },
  {
    id: 'glass',
    title: 'Dynamic Glass',
    icon: 'glass',
    children: [
      { id: 'glass-aurora', title: 'Aurora Flow', action: () => setGlassPreset('aurora') },
      { id: 'glass-crystal', title: 'Crystal Depth', action: () => setGlassPreset('crystal') },
      { id: 'glass-frost', title: 'Frost Mist', action: () => setGlassPreset('frost') },
      { id: 'glass-motion-on', title: 'Enable Motion', action: () => setGlassMotion(true) },
      { id: 'glass-motion-off', title: 'Reduce Motion', action: () => setGlassMotion(false) }
    ]
  },
  {
    id: 'playground',
    title: '休闲舱',
    icon: 'playground',
    children: [
      { id: 'play-home', title: '游乐场大厅', action: goPlayground },
      { id: 'play-gomoku', title: '五子棋', action: goGomoku },
      { id: 'play-ttt', title: '井字棋', action: goTicTacToe },
      { id: 'play-connect4', title: '四子棋', action: goConnectFour }
    ]
  }
]

const activeMenu = computed(() => (
  menuItems.find((item) => item.id === activeMenuId.value && Array.isArray(item.children)) || null
))

const handleMainItemClick = (item) => {
  if (item.children?.length) {
    activeMenuId.value = activeMenuId.value === item.id ? null : item.id
    return
  }
  item.action?.()
}

const handleEsc = (event) => {
  if (event.key === 'Escape') closeSideMenu()
}

watch(() => route.path, () => {
  closeSideMenu()
  syncMailPolling()
})

watch(sideMenuOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

onMounted(() => {
  window.addEventListener('keydown', handleEsc)
  applyGlassAppearance()
  syncMailPolling()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleEsc)
  document.body.style.overflow = ''
  document.documentElement.removeAttribute('data-glass-preset')
  document.documentElement.classList.remove('glass-motion-off')
  mailStore.stopPolling()
})
</script>

<template>
  <router-view />

  <button
    v-if="showFloatingMenu"
    type="button"
    class="liquid-menu-trigger"
    :class="{ open: sideMenuOpen }"
    aria-label="Open side menu"
    @click="toggleSideMenu"
  >
    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
      <path d="M4 6h16M4 12h16M4 18h16" stroke-linecap="round" />
    </svg>
  </button>

  <!-- Top-right action bar -->
  <transition
    enter-active-class="transition duration-220 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-180 ease-out"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="showFloatingMenu && sideMenuOpen" class="liquid-menu-backdrop fixed inset-0 z-[130]" @click="closeSideMenu">
      <div class="relative h-full" @click.stop>
        <aside class="liquid-side-rail h-full w-[88px] py-6">
          <nav class="mt-2 flex flex-col items-center gap-4 px-4">
            <button
              v-for="item in menuItems"
              :key="item.id"
              type="button"
              class="liquid-rail-btn h-[52px] w-[52px] rounded-2xl flex items-center justify-center transition-all"
              :class="activeMenuId === item.id
                ? 'is-active text-sky-100'
                : 'text-slate-300 hover:text-white'"
              :title="item.title"
              @click="handleMainItemClick(item)"
            >
              <span class="menu-icon-shell">
                <template v-if="item.icon === 'core'">
                  <svg class="menu-glyph" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path class="tone-soft" d="M12 3.2 4.8 6.7 12 10.1l7.2-3.4L12 3.2Z" stroke-width="1.7" />
                    <path d="M4.8 11.2 12 7.8l7.2 3.4L12 14.6l-7.2-3.4Z" stroke-width="1.7" />
                    <path class="tone-bright" d="M4.8 15.8 12 12.4l7.2 3.4L12 19.2l-7.2-3.4Z" stroke-width="1.7" />
                  </svg>
                </template>
                <template v-else-if="item.icon === 'world'">
                  <svg class="menu-glyph" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="8.4" stroke-width="1.7" />
                    <path class="tone-soft" d="M3.8 12h16.4M12 3.8c2.1 2.2 3.3 5.1 3.3 8.2 0 3.1-1.2 6-3.3 8.2M12 3.8c-2.1 2.2-3.3 5.1-3.3 8.2 0 3.1 1.2 6 3.3 8.2" stroke-width="1.6" />
                  </svg>
                </template>
                <template v-else-if="item.icon === 'ai'">
                  <svg class="menu-glyph" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <rect x="6.2" y="7.2" width="11.6" height="9.6" rx="3.4" stroke-width="1.7" />
                    <path class="tone-soft" d="M9.3 12h5.4M12 4.2v2M8.8 18.8v1.7m6.4-1.7v1.7M5.1 12H3.5m17 0h-1.6" stroke-width="1.6" />
                    <circle class="tone-bright" cx="12" cy="12" r="1.2" stroke-width="1.5" />
                  </svg>
                </template>
                <template v-else-if="item.icon === 'fleet'">
                  <svg class="menu-glyph" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M12 4.2 18.6 8v8L12 19.8 5.4 16V8L12 4.2Z" stroke-width="1.7" />
                    <path class="tone-soft" d="M12 4.2v15.6M5.4 8 12 12l6.6-4" stroke-width="1.6" />
                    <circle class="tone-bright" cx="12" cy="12" r="1.5" stroke-width="1.5" />
                  </svg>
                </template>
                <template v-else-if="item.icon === 'growth'">
                  <svg class="menu-glyph" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path class="tone-soft" d="M4 19.2h16" stroke-width="1.6" />
                    <path d="m6.6 15.2 3.6-3.5 2.8 2.6 4.4-5" stroke-width="1.8" />
                    <path class="tone-bright" d="m16.3 9.3 1.1-.1-.1 1.1" stroke-width="1.7" />
                  </svg>
                </template>
                <template v-else-if="item.icon === 'glass'">
                  <svg class="menu-glyph" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M12 3.8c-3.9 4.1-5.9 7-5.9 9.2a5.9 5.9 0 1 0 11.8 0c0-2.2-2-5.1-5.9-9.2Z" stroke-width="1.7" />
                    <path class="tone-soft" d="M9.7 12.3c.3-1 1-2.2 2.3-3.8m-3 7.3c0 1.4 1.1 2.5 2.5 2.5" stroke-width="1.55" />
                  </svg>
                </template>
                <template v-else>
                  <svg class="menu-glyph" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <rect x="4.2" y="9.4" width="15.6" height="8.4" rx="3.5" stroke-width="1.7" />
                    <path class="tone-soft" d="M8.2 9.4V7.8a3.8 3.8 0 0 1 7.6 0v1.6M8.8 13.6h.01M15.2 13.6h.01" stroke-width="1.6" />
                  </svg>
                </template>
              </span>
            </button>
          </nav>
        </aside>

        <transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="opacity-0 -translate-x-5 scale-97"
          enter-to-class="opacity-100 translate-x-0 scale-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="opacity-100 translate-x-0 scale-100"
          leave-to-class="opacity-0 -translate-x-5 scale-97"
        >
          <section
            v-if="activeMenu"
            class="liquid-flyout absolute left-24 top-4 z-[141] w-80 rounded-3xl p-5"
          >
            <div class="mb-4 px-1 text-xs font-semibold uppercase tracking-[0.25em] text-sky-400/70">{{ activeMenu.title }}</div>
            <div class="flex flex-col gap-1.5">
              <button
                v-for="entry in activeMenu.children"
                :key="entry.id"
                type="button"
                class="liquid-flyout-item group flex w-full items-center justify-between rounded-2xl px-4 py-3.5 text-left text-[15px] text-slate-100 transition-all hover:text-white"
                @click="entry.action()"
              >
                <span>{{ entry.title }}</span>
                <svg class="h-5 w-5 text-slate-600 transition-transform group-hover:translate-x-1 group-hover:text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="m9 6 6 6-6 6" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>
            </div>
          </section>
        </transition>
      </div>
    </div>
  </transition>

  <DimensionTransitionOverlay />
  <BackgroundMusic />
</template>

<style>
html, body {
  margin: 0;
  padding: 0;
  overflow-x: hidden;
  overflow-y: auto !important;
  min-height: 100%;
}

#app {
  width: 100%;
  min-height: 100%;
  overflow-y: auto;
}
</style>

<style>

/* Liquid glass menu system */
:root {
  --glass-accent: rgba(125, 211, 252, 0.86);
  --glass-glow: rgba(56, 189, 248, 0.24);
  --glass-menu-top: rgba(37, 99, 235, 0.28);
  --glass-menu-bottom: rgba(15, 23, 42, 0.42);
  --glass-rail-top: rgba(37, 99, 235, 0.22);
  --glass-rail-bottom: rgba(15, 23, 42, 0.48);
}

:root[data-glass-preset='aurora'] {
  --glass-accent: rgba(56, 189, 248, 0.88);
  --glass-glow: rgba(34, 211, 238, 0.3);
  --glass-menu-top: rgba(14, 165, 233, 0.24);
  --glass-menu-bottom: rgba(29, 78, 216, 0.34);
  --glass-rail-top: rgba(14, 165, 233, 0.2);
  --glass-rail-bottom: rgba(30, 41, 59, 0.5);
}

:root[data-glass-preset='crystal'] {
  --glass-accent: rgba(167, 243, 208, 0.9);
  --glass-glow: rgba(52, 211, 153, 0.27);
  --glass-menu-top: rgba(16, 185, 129, 0.24);
  --glass-menu-bottom: rgba(6, 78, 59, 0.42);
  --glass-rail-top: rgba(52, 211, 153, 0.22);
  --glass-rail-bottom: rgba(6, 78, 59, 0.5);
}

:root[data-glass-preset='frost'] {
  --glass-accent: rgba(191, 219, 254, 0.92);
  --glass-glow: rgba(148, 163, 184, 0.26);
  --glass-menu-top: rgba(148, 163, 184, 0.22);
  --glass-menu-bottom: rgba(30, 41, 59, 0.4);
  --glass-rail-top: rgba(148, 163, 184, 0.18);
  --glass-rail-bottom: rgba(15, 23, 42, 0.48);
}
.liquid-menu-trigger {
  position: fixed;
  left: 16px;
  bottom: 16px;
  z-index: 140;
  display: inline-flex;
  width: 46px;
  height: 46px;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  color: rgba(224, 242, 254, 0.96);
  border: 1px solid rgba(187, 247, 255, 0.44);
  background:
    linear-gradient(150deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.04)),
    linear-gradient(180deg, var(--glass-menu-top), var(--glass-menu-bottom));
  box-shadow:
    0 14px 34px rgba(2, 6, 23, 0.52),
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    inset 0 -10px 18px rgba(2, 6, 23, 0.32);
  backdrop-filter: saturate(180%) blur(18px);
  -webkit-backdrop-filter: saturate(180%) blur(18px);
  transition: transform 0.2s ease-out, border-color 0.2s ease-out, box-shadow 0.2s ease-out, color 0.2s ease-out;
  overflow: hidden;
}

.liquid-menu-trigger::before {
  content: '';
  position: absolute;
  inset: -30%;
  background: radial-gradient(circle, var(--glass-glow), transparent 62%);
  opacity: 0.6;
  pointer-events: none;
  animation: glass-orbit 7s linear infinite;
}

.liquid-menu-trigger::after {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: 15px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  pointer-events: none;
}

.liquid-menu-trigger:hover {
  transform: translateY(-2px);
  border-color: rgba(224, 242, 254, 0.78);
  box-shadow:
    0 18px 38px rgba(2, 6, 23, 0.58),
    0 0 22px rgba(56, 189, 248, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.58),
    inset 0 -10px 18px rgba(2, 6, 23, 0.3);
}

.liquid-menu-trigger.open {
  border-color: var(--glass-accent);
  color: #ffffff;
  box-shadow:
    0 18px 40px rgba(2, 6, 23, 0.58),
    0 0 24px var(--glass-glow),
    inset 0 1px 0 rgba(255, 255, 255, 0.62),
    inset 0 -12px 22px rgba(14, 116, 144, 0.36);
}

.liquid-menu-backdrop {
  background:
    radial-gradient(circle at left 18%, rgba(56, 189, 248, 0.12), transparent 36%),
    rgba(2, 6, 23, 0.48);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
}

.liquid-side-rail {
  position: relative;
  border-right: 1px solid rgba(186, 230, 253, 0.18);
  background:
    linear-gradient(180deg, rgba(148, 163, 184, 0.14), rgba(30, 41, 59, 0.16) 46%, rgba(15, 23, 42, 0.42)),
    linear-gradient(165deg, var(--glass-rail-top), var(--glass-rail-bottom));
  box-shadow:
    14px 0 30px rgba(2, 6, 23, 0.36),
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    inset -1px 0 0 rgba(255, 255, 255, 0.08);
  backdrop-filter: saturate(175%) blur(20px);
  -webkit-backdrop-filter: saturate(175%) blur(20px);
}

.liquid-side-rail::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.02) 28%, transparent 52%);
  pointer-events: none;
}

.liquid-rail-btn {
  position: relative;
  border: 1px solid rgba(186, 230, 253, 0.24);
  background:
    linear-gradient(155deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.03)),
    linear-gradient(180deg, rgba(15, 23, 42, 0.38), rgba(15, 23, 42, 0.52));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.44),
    inset 0 -10px 18px rgba(2, 6, 23, 0.28);
  backdrop-filter: saturate(170%) blur(14px);
  -webkit-backdrop-filter: saturate(170%) blur(14px);
  overflow: hidden;
}

.liquid-rail-btn::before {
  content: '';
  position: absolute;
  inset: -40%;
  background: radial-gradient(circle, var(--glass-glow), transparent 58%);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s ease;
}

.liquid-rail-btn:hover {
  border-color: rgba(224, 242, 254, 0.56);
  box-shadow:
    0 0 18px var(--glass-glow),
    inset 0 1px 0 rgba(255, 255, 255, 0.54),
    inset 0 -10px 18px rgba(2, 6, 23, 0.22);
}

.liquid-rail-btn:hover::before {
  opacity: 0.8;
}

.liquid-rail-btn.is-active {
  border-color: var(--glass-accent);
  background:
    linear-gradient(155deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.08)),
    linear-gradient(180deg, rgba(14, 116, 144, 0.26), rgba(30, 64, 175, 0.34));
  box-shadow:
    0 0 20px var(--glass-glow),
    inset 0 1px 0 rgba(255, 255, 255, 0.62),
    inset 0 -12px 20px rgba(2, 6, 23, 0.24);
}

.liquid-rail-btn.is-active::before {
  opacity: 0.95;
}

.menu-icon-shell {
  position: relative;
  z-index: 1;
  display: inline-flex;
  width: 24px;
  height: 24px;
  align-items: center;
  justify-content: center;
}

.menu-glyph {
  width: 21px;
  height: 21px;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 2px 6px rgba(2, 6, 23, 0.35));
}

.menu-glyph .tone-soft {
  stroke: rgba(191, 219, 254, 0.82);
}

.menu-glyph .tone-bright {
  stroke: var(--glass-accent);
}

.liquid-flyout {
  position: relative;
  border: 1px solid rgba(186, 230, 253, 0.3);
  background:
    linear-gradient(150deg, rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.06)),
    linear-gradient(180deg, rgba(30, 64, 175, 0.16), rgba(15, 23, 42, 0.44));
  box-shadow:
    0 26px 56px rgba(2, 6, 23, 0.62),
    0 0 24px rgba(56, 189, 248, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.52),
    inset 0 -14px 28px rgba(2, 6, 23, 0.3);
  backdrop-filter: saturate(185%) blur(24px);
  -webkit-backdrop-filter: saturate(185%) blur(24px);
}

.liquid-flyout::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.01) 34%, transparent 60%);
  pointer-events: none;
}

.liquid-flyout-item {
  position: relative;
  border: 1px solid rgba(148, 163, 184, 0.1);
  background: rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.liquid-flyout-item:hover {
  border-color: rgba(125, 211, 252, 0.38);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.04)),
    rgba(14, 116, 144, 0.24);
  box-shadow:
    0 8px 22px rgba(2, 6, 23, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.42);
}

@keyframes glass-orbit {
  from { transform: rotate(0deg) scale(1); }
  50% { transform: rotate(180deg) scale(1.06); }
  to { transform: rotate(360deg) scale(1); }
}

.glass-motion-off .liquid-menu-trigger::before,
.glass-motion-off .liquid-rail-btn::before {
  animation: none !important;
  opacity: 0 !important;
}

.glass-motion-off .liquid-menu-trigger,
.glass-motion-off .liquid-rail-btn,
.glass-motion-off .liquid-flyout,
.glass-motion-off .liquid-flyout-item {
  transition-duration: 0.01ms !important;
}

@media (max-width: 768px) {
  .liquid-menu-trigger {
    left: 12px;
    bottom: 12px;
  }
}
</style>
