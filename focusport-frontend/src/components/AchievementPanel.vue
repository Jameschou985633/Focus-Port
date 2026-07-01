<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { achievementApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const achievements = ref([])
const userAchievements = ref([])
const isLoading = ref(false)

const categories = ['general', 'focus', 'streak', 'level', 'social', 'special']
const activeCategory = ref('all')

const loadAchievements = async () => {
  isLoading.value = true
  try {
    const [allRes, userRes] = await Promise.all([
      achievementApi.all(),
      achievementApi.user(userStore.username)
    ])
    achievements.value = allRes.data.achievements || []
    userAchievements.value = userRes.data.unlocked || []
  } catch (error) {
    console.error('加载成就失败:', error)
  } finally {
    isLoading.value = false
  }
}

const isUnlocked = (achievementId) => {
  return userAchievements.value.some(a => a.achievement_id === achievementId)
}

const filteredAchievements = computed(() => {
  if (activeCategory.value === 'all') return achievements.value
  return achievements.value.filter(a => a.category === activeCategory.value)
})

const unlockedCount = computed(() => userAchievements.value.length)
const totalCount = computed(() => achievements.value.length)
const progressPercent = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round(unlockedCount.value / totalCount.value * 100)
})

const selectedAchievement = ref(null)

const openDetail = (achievement) => {
  selectedAchievement.value = achievement
}

const closeDetail = () => {
  selectedAchievement.value = null
}

const getUnlockDate = (achievementId) => {
  const ua = userAchievements.value.find(a => a.achievement_id === achievementId)
  return ua?.unlocked_at || ua?.unlocked_date || null
}

const goBack = () => router.push('/')

onMounted(() => loadAchievements())
</script>

<template>
  <div class="achievements-container">
    <div class="achievements-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>🏆 成就墙</h1>
      <div class="progress-info">
        <span>{{ unlockedCount }}/{{ totalCount }}</span>
        <span class="progress-percent">{{ progressPercent }}%</span>
      </div>
    </div>

    <div class="progress-bar-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
    </div>

    <div class="category-tabs">
      <button :class="{ active: activeCategory === 'all' }" @click="activeCategory = 'all'">全部</button>
      <button v-for="cat in categories" :key="cat" :class="{ active: activeCategory === cat }" @click="activeCategory = cat">
        {{ cat }}
      </button>
    </div>

    <div class="achievements-grid">
      <div
        v-for="achievement in filteredAchievements"
        :key="achievement.id"
        :class="['achievement-card', { unlocked: isUnlocked(achievement.id) }]"
        @click="openDetail(achievement)"
      >
        <div class="achievement-icon">{{ isUnlocked(achievement.id) ? achievement.icon : '🔒' }}</div>
        <div class="achievement-info">
          <div class="achievement-name">{{ isUnlocked(achievement.id) ? achievement.name : '???' }}</div>
          <div class="achievement-desc">{{ isUnlocked(achievement.id) ? achievement.description : '继续努力解锁' }}</div>
          <div class="achievement-reward" v-if="isUnlocked(achievement.id)">
            +{{ achievement.exp_reward }} EXP
          </div>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>

    <!-- Achievement Detail Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="selectedAchievement" class="detail-overlay" @click.self="closeDetail">
          <div class="detail-card">
            <button class="detail-close" @click="closeDetail">×</button>
            <div class="detail-icon-wrap">
              <span class="detail-icon">{{ isUnlocked(selectedAchievement.id) ? selectedAchievement.icon : '🔒' }}</span>
            </div>
            <h2 class="detail-name">{{ isUnlocked(selectedAchievement.id) ? selectedAchievement.name : '???' }}</h2>
            <p class="detail-desc">{{ selectedAchievement.description || '继续努力解锁这个成就' }}</p>
            <div class="detail-meta">
              <span class="detail-badge category">{{ selectedAchievement.category }}</span>
              <span class="detail-badge exp">+{{ selectedAchievement.exp_reward || 0 }} EXP</span>
              <span v-if="isUnlocked(selectedAchievement.id)" class="detail-badge unlocked">已解锁 ✅</span>
              <span v-else class="detail-badge locked">未解锁</span>
            </div>
            <p v-if="getUnlockDate(selectedAchievement.id)" class="detail-date">
              解锁于 {{ getUnlockDate(selectedAchievement.id) }}
            </p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.achievements-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  color: white;
}

.achievements-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  margin-bottom: 16px;
}

.back-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
}

h1 { margin: 0; font-size: 24px; }

.progress-info { text-align: right; }
.progress-percent { color: #4ade80; font-weight: 700; margin-left: 8px; }

.progress-bar-container { margin-bottom: 16px; }
.progress-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ade80, #22d3ee);
  transition: width 0.5s;
}

.category-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.category-tabs button {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 8px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}

.category-tabs button.active {
  background: rgba(74, 222, 128, 0.25);
  border-color: rgba(74, 222, 128, 0.5);
}

.achievements-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.achievement-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  gap: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s;
}

.achievement-card.unlocked {
  background: rgba(74, 222, 128, 0.15);
  border-color: rgba(74, 222, 128, 0.3);
}

.achievement-icon {
  font-size: 40px;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 14px;
}

.achievement-info { flex: 1; }
.achievement-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}
.achievement-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 8px;
}
.achievement-reward {
  font-size: 12px;
  color: #fbbf24;
  font-weight: 600;
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

.achievement-card { cursor: pointer; }
.achievement-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }

/* Detail Modal */
.detail-overlay {
  position: fixed; inset: 0;
  background: rgba(2, 6, 23, 0.75);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: 20px;
}

.detail-card {
  position: relative;
  width: 100%; max-width: 360px;
  background: linear-gradient(180deg, #0f172a, #1e293b);
  border: 1.5px solid rgba(129, 214, 255, 0.34);
  border-radius: 24px;
  padding: 32px 24px;
  text-align: center;
  box-shadow: 0 24px 48px rgba(0,0,0,0.5);
}

.detail-close {
  position: absolute; top: 16px; right: 16px;
  width: 32px; height: 32px;
  background: rgba(255,255,255,0.05); border: none; border-radius: 8px;
  color: rgba(222,240,255,0.7); font-size: 20px; cursor: pointer;
}
.detail-close:hover { background: rgba(255,255,255,0.1); }

.detail-icon-wrap {
  width: 80px; height: 80px; margin: 0 auto 16px;
  display: grid; place-items: center;
  background: rgba(255,255,255,0.08); border-radius: 20px;
}

.detail-icon { font-size: 48px; }
.detail-name { margin: 0 0 8px; font-size: 20px; }
.detail-desc { margin: 0 0 16px; color: rgba(222,240,255,0.7); font-size: 14px; line-height: 1.6; }

.detail-meta { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 12px; }

.detail-badge {
  padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: 600;
}
.detail-badge.category { background: rgba(59,130,246,0.2); color: #93c5fd; }
.detail-badge.exp { background: rgba(251,191,36,0.2); color: #fbbf24; }
.detail-badge.unlocked { background: rgba(74,222,128,0.2); color: #4ade80; }
.detail-badge.locked { background: rgba(255,255,255,0.06); color: rgba(222,240,255,0.5); }

.detail-date { margin: 0; font-size: 12px; color: rgba(222,240,255,0.4); }

.modal-enter-active, .modal-leave-active { transition: all 0.25s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .detail-card, .modal-leave-to .detail-card { transform: scale(0.95); }
</style>
