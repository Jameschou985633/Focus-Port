<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BackgroundMusic from './components/BackgroundMusic.vue'
import DimensionTransitionOverlay from './components/DimensionTransitionOverlay.vue'
import { useMailStore } from './stores/mail'
import { useUserStore } from './stores/user'

const route = useRoute()
const router = useRouter()
const mailStore = useMailStore()
const userStore = useUserStore()

const isAdminRoute = computed(() => route.path === '/admin')
const showBackgroundMusic = computed(() => !isAdminRoute.value)
const routesMissingBackLabel = new Set(['Island', 'CollabTimer'])

const showGlobalBackLabel = computed(() => routesMissingBackLabel.has(String(route.name || '')))

const globalBackTarget = computed(() => {
  if (route.path.startsWith('/collab/')) return '/collab'
  if (route.path.startsWith('/playground/')) return '/playground'
  return '/'
})

const goGlobalBack = () => {
  router.push(globalBackTarget.value)
}

const syncMailPolling = () => {
  const username = userStore.username && userStore.username !== 'guest' ? userStore.username : ''
  if (username) {
    mailStore.startPolling(username)
    return
  }
  mailStore.stopPolling()
}

watch(() => route.path, syncMailPolling)
watch(() => userStore.username, syncMailPolling)

onMounted(syncMailPolling)

onUnmounted(() => {
  mailStore.stopPolling()
})
</script>

<template>
  <button
    v-if="showGlobalBackLabel"
    type="button"
    class="global-back-label"
    @click="goGlobalBack"
  >
    <span>←</span>
    <strong>返回</strong>
  </button>
  <router-view />
  <DimensionTransitionOverlay />
  <BackgroundMusic v-if="showBackgroundMusic" />
</template>

<style>
html,
body {
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

.global-back-label {
  position: fixed;
  top: 16px;
  left: 16px;
  z-index: 120;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 44px;
  padding: 0 22px;
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  cursor: pointer;
  font-family: inherit;
  font-size: 20px;
  font-weight: 800;
  line-height: 1;
}

.global-back-label:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: rgba(255, 255, 255, 0.38);
}

.global-back-label span {
  font-size: 22px;
  line-height: 1;
}

.global-back-label strong {
  font-size: 20px;
  font-weight: 800;
}

@media (max-width: 720px) {
  .global-back-label {
    top: 12px;
    left: 12px;
    min-height: 40px;
    padding: 0 16px;
    font-size: 17px;
  }

  .global-back-label strong {
    font-size: 17px;
  }
}
</style>
