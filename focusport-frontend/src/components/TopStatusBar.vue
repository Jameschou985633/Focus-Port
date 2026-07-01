<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const router = useRouter()
const userStore = useUserStore()

const props = defineProps({
  focusEnergy: { type: Number, default: 0 },
  focusMinutes: { type: Number, default: 0 },
  streakDays: { type: Number, default: 0 }
})

const currentTime = ref(new Date())

const formattedDate = computed(() => {
  const d = currentTime.value
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.getMonth() + 1}/${d.getDate()} ${weekdays[d.getDay()]}`
})

const formattedFocusTime = computed(() => {
  const hours = Math.floor(props.focusMinutes / 60)
  const mins = props.focusMinutes % 60
  return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
})

const goToControl = () => router.push('/more')

const logout = () => {
  if (!window.confirm('确认退出当前舰桥账号吗？')) return
  userStore.logout()
  router.push('/login')
}

let timer = null
onMounted(() => {
  timer = setInterval(() => {
    currentTime.value = new Date()
  }, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="top-status-bar">
    <div class="left-zone">
      <span class="date-text">{{ formattedDate }}</span>
      <button type="button" class="user-pill" @click="logout">
        <span class="user-avatar">舰</span>
        <span class="user-copy">
          <small>{{ composeWorldLabel(WORLD_NAMES.captainLog) }}</small>
          <strong>{{ userStore.username }}</strong>
        </span>
      </button>
    </div>

    <div class="stats-zone">
      <div class="stat-card energy">
        <span class="label">{{ WORLD_NAMES.currency.zh }} · {{ WORLD_NAMES.currency.en }}</span>
        <strong>{{ focusEnergy }}</strong>
      </div>
      <div class="stat-card">
        <span class="label">{{ composeWorldLabel(WORLD_NAMES.voyageRecord) }}</span>
        <strong>{{ formattedFocusTime }}</strong>
      </div>
      <div class="stat-card">
        <span class="label">{{ composeWorldLabel(WORLD_NAMES.streak) }}</span>
        <strong>{{ streakDays }} 天</strong>
      </div>
    </div>

    <div class="right-zone">
      <button type="button" class="control-btn" :title="composeWorldLabel(WORLD_NAMES.protocolStation)" @click="goToControl">
        {{ composeWorldLabel(WORLD_NAMES.protocolStation) }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.top-status-bar {
  position: fixed;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  width: min(1180px, calc(100vw - 24px));
  min-height: 58px;
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 16px;
  background:
    linear-gradient(180deg, rgba(10, 22, 52, 0.92), rgba(5, 10, 24, 0.94)),
    rgba(8, 14, 28, 0.8);
  border: 1.5px solid rgba(125, 220, 255, 0.2);
  box-shadow: 0 18px 48px rgba(4, 8, 22, 0.36);
  backdrop-filter: blur(20px);
}

.left-zone,
.stats-zone,
.right-zone {
  display: flex;
  align-items: center;
  gap: 10px;
}

.date-text {
  font-size: 13px;
  color: rgba(222, 240, 255, 0.72);
}

.user-pill,
.control-btn {
  border: none;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  color: #eef7ff;
  padding: 10px 14px;
  cursor: pointer;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.user-copy small,
.label {
  font-family: 'Roboto Mono', 'Consolas', monospace;
  font-size: 10px;
  color: rgba(196, 245, 255, 0.74);
  text-shadow: 0 0 12px rgba(0, 255, 255, 0.14);
}

.user-copy strong {
  font-size: 13px;
}

.user-avatar {
  width: 24px;
  height: 24px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(76, 222, 255, 0.16);
  font-size: 12px;
  font-weight: 800;
}

.stat-card {
  min-width: 128px;
  border-radius: 16px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-card.energy {
  background: rgba(76, 222, 255, 0.1);
}

.stat-card strong {
  font-size: 15px;
}

.control-btn {
  max-width: 240px;
  font-size: 12px;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .top-status-bar {
    top: 8px;
    width: calc(100vw - 16px);
    min-height: 52px;
    padding: 8px 12px;
    gap: 8px;
  }

  .date-text,
  .control-btn {
    display: none;
  }

  .stats-zone {
    flex: 1;
    justify-content: center;
  }

  .stat-card {
    min-width: 84px;
    padding: 7px 9px;
  }

  .label {
    font-size: 9px;
  }
}
</style>
