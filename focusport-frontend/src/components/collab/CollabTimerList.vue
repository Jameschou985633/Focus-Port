<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import SpaceButton from '../base/SpaceButton.vue'
import SpaceCard from '../base/SpaceCard.vue'
import SpaceModal from '../base/SpaceModal.vue'
import StarshipArchivePlaceholder from './StarshipArchivePlaceholder.vue'
import CircleFeed from './CircleFeed.vue'
import { WORLD_NAMES, composeWorldLabel } from '../../constants/worldNames'

const router = useRouter()
const currentUsername = ref(localStorage.getItem('username') || 'guest')
const rooms = ref([])
const isLoading = ref(true)
const showCreateModal = ref(false)
const userSunshine = ref(0)
const errorMessage = ref('')
const activeTab = ref('rooms')

const tabs = [
  { value: 'rooms', label: '协作房间', icon: '🚀' },
  { value: 'circle', label: '星桥圈子', icon: '💬' }
]

const switchTab = (value) => {
  activeTab.value = value
}

const newRoom = ref({
  name: '',
  description: '',
  max_seats: 4,
  is_public: true,
  password: '',
  theme: 'space'
})

const themes = [
  { value: 'space', label: 'Deep Space Port', icon: 'ORBIT' },
  { value: 'nebula', label: 'Nebula Dock', icon: 'NEB' },
  { value: 'mars', label: 'Mars Relay', icon: 'MRS' },
  { value: 'lunar', label: 'Lunar Bay', icon: 'LNR' }
]

const roomCountLabel = computed(() => `${rooms.value.length} ACTIVE BERTHS`)

const loadRooms = async () => {
  isLoading.value = true
  try {
    const res = await axios.get('/api/greenhouse/list', { params: { is_public: true } })
    rooms.value = res.data.greenhouses || []
  } catch (error) {
    console.error('Failed to load Fleet Nexus rooms:', error)
  } finally {
    isLoading.value = false
  }
}

const loadUserSunshine = async () => {
  try {
    const res = await axios.get(`/api/greenhouse/sunshine/${currentUsername.value}`)
    userSunshine.value = res.data.sunshine || 0
  } catch (error) {
    console.error('Failed to load sunshine balance:', error)
  }
}

const createRoom = async () => {
  if (!newRoom.value.name.trim()) {
    errorMessage.value = 'Please enter a fleet berth name.'
    return
  }

  errorMessage.value = ''
  isLoading.value = true

  try {
    const res = await axios.post('/api/greenhouse/create', {
      name: newRoom.value.name,
      description: newRoom.value.description,
      max_seats: newRoom.value.max_seats,
      is_public: newRoom.value.is_public,
      password: newRoom.value.password,
      theme: newRoom.value.theme,
      owner_username: currentUsername.value
    })

    if (res.data.success) {
      showCreateModal.value = false
      newRoom.value = {
        name: '',
        description: '',
        max_seats: 4,
        is_public: true,
        password: '',
        theme: 'space'
      }
      await loadRooms()
    }
  } catch (error) {
    errorMessage.value = error.response?.data?.error || 'Failed to create fleet berth.'
  } finally {
    isLoading.value = false
  }
}

const joinRoom = (roomId) => {
  router.push(`/collab/${roomId}`)
}

const getThemeIcon = (theme) => {
  const match = themes.find((item) => item.value === theme)
  return match?.icon || 'ORBIT'
}

onMounted(() => {
  loadRooms()
  loadUserSunshine()
})
</script>

<template>
  <div class="fleet-page">
    <div class="stars-bg"></div>

    <section class="hero-panel">
      <div class="hero-copy">
        <p class="hero-kicker">{{ WORLD_NAMES.fleetNexus.en }}</p>
        <h1>{{ composeWorldLabel(WORLD_NAMES.fleetNexus) }}</h1>
        <p>
          Dock with other commanders, inspect live berths, and relay your station status into the shared ring.
        </p>
      </div>

      <div class="hero-status">
        <div class="status-chip">
          <span>{{ WORLD_NAMES.currency.zh }}</span>
          <strong>{{ userSunshine }}</strong>
        </div>
        <div class="status-chip secondary">
          <span>Berths</span>
          <strong>{{ roomCountLabel }}</strong>
        </div>
      </div>
    </section>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === tab.value }"
        @click="activeTab = tab.value"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
      </button>
    </div>

    <!-- 圈子内容 -->
    <section v-if="activeTab === 'circle'" class="circle-section">
      <CircleFeed />
    </section>

    <!-- 房间内容 -->
    <section v-show="activeTab === 'rooms'" class="rooms-shell">
      <div class="section-header">
        <div>
          <p class="section-kicker">DOCK GRID</p>
          <h2>Public Fleet Berths</h2>
        </div>
        <SpaceButton variant="success" @click="showCreateModal = true">
          + Open New Berth
        </SpaceButton>
      </div>

      <div v-if="isLoading" class="loading-state">
        <div class="space-spinner"></div>
        <p>Linking to Fleet Nexus...</p>
      </div>

      <div v-else-if="rooms.length" class="rooms-grid">
        <SpaceCard
          v-for="room in rooms"
          :key="room.id"
          :title="room.name"
          :subtitle="room.description || 'Fleet briefing channel open.'"
          :icon="getThemeIcon(room.theme)"
          variant="primary"
          clickable
          @click="joinRoom(room.id)"
        >
          <div class="room-meta">
            <span class="online-count">
              <span class="status-dot online"></span>
              {{ room.current_users || 0 }}/{{ room.max_seats }} docked
            </span>
            <span class="room-visibility">{{ room.is_public === false ? 'Restricted' : 'Open Relay' }}</span>
          </div>
        </SpaceCard>
      </div>

      <div v-else class="empty-state">
        <div class="empty-icon">NEXUS</div>
        <p>No active berths. Open the first Fleet Nexus room and broadcast a mission lane.</p>
      </div>
    </section>

    <StarshipArchivePlaceholder :rooms="rooms" />

    <SpaceModal v-model:visible="showCreateModal" :title="composeWorldLabel(WORLD_NAMES.fleetNexus)" width="460px">
      <div class="form-group">
        <label>Berth Name</label>
        <input v-model="newRoom.name" type="text" maxlength="20" placeholder="Morning Differential Squad" class="space-input">
      </div>

      <div class="form-group">
        <label>Mission Brief</label>
        <input v-model="newRoom.description" type="text" maxlength="50" placeholder="Optional relay note" class="space-input">
      </div>

      <div class="form-group">
        <label>Seat Capacity</label>
        <select v-model="newRoom.max_seats" class="space-select">
          <option :value="2">2 seats</option>
          <option :value="4">4 seats</option>
          <option :value="6">6 seats</option>
          <option :value="8">8 seats</option>
        </select>
      </div>

      <div class="form-group">
        <label>Dock Theme</label>
        <div class="theme-selector">
          <button
            v-for="theme in themes"
            :key="theme.value"
            type="button"
            class="theme-btn"
            :class="{ active: newRoom.theme === theme.value }"
            @click="newRoom.theme = theme.value"
          >
            {{ theme.icon }} {{ theme.label }}
          </button>
        </div>
      </div>

      <div class="form-group">
        <label class="checkbox-label">
          <input v-model="newRoom.is_public" type="checkbox">
          Public relay berth
        </label>
      </div>

      <div v-if="!newRoom.is_public" class="form-group">
        <label>Access Key</label>
        <input v-model="newRoom.password" type="password" placeholder="Restricted berth password" class="space-input">
      </div>

      <p v-if="errorMessage" class="error-msg">{{ errorMessage }}</p>

      <div class="modal-actions">
        <SpaceButton variant="secondary" @click="showCreateModal = false">Cancel</SpaceButton>
        <SpaceButton variant="primary" :disabled="isLoading" @click="createRoom">
          {{ isLoading ? 'Deploying...' : 'Deploy To Fleet Nexus' }}
        </SpaceButton>
      </div>
    </SpaceModal>
  </div>
</template>

<style scoped>
.fleet-page {
  min-height: 100vh;
  padding: 28px 20px 36px;
  background: linear-gradient(180deg, #050914 0%, #08111f 48%, #0a192f 100%);
  position: relative;
  overflow: hidden;
}

.stars-bg {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(2px 2px at 20px 30px, rgba(255, 255, 255, 0.92), transparent),
    radial-gradient(1px 1px at 90px 40px, rgba(255, 255, 255, 0.82), transparent),
    radial-gradient(2px 2px at 160px 120px, rgba(255, 255, 255, 0.55), transparent),
    radial-gradient(1px 1px at 260px 60px, rgba(255, 255, 255, 0.76), transparent);
  background-size: 360px 220px;
  opacity: 0.55;
  pointer-events: none;
}

.hero-panel,
.rooms-shell {
  position: relative;
  z-index: 1;
  max-width: 980px;
  margin: 0 auto 22px;
  border-radius: 26px;
  padding: 22px;
  background:
    linear-gradient(180deg, rgba(10, 26, 46, 0.96), rgba(6, 13, 30, 0.98)),
    rgba(4, 9, 20, 0.92);
  border: 1px solid rgba(0, 255, 255, 0.16);
  box-shadow: 0 24px 56px rgba(2, 8, 18, 0.32);
}

.hero-panel {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.hero-kicker,
.section-kicker {
  margin: 0 0 8px;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: rgba(164, 245, 255, 0.68);
}

.hero-panel h1,
.section-header h2 {
  margin: 0;
  color: #eefcff;
  text-shadow: 0 0 16px rgba(0, 255, 255, 0.2);
}

.hero-copy p:last-child {
  margin: 10px 0 0;
  max-width: 620px;
  line-height: 1.6;
  color: rgba(214, 247, 255, 0.72);
}

.hero-status {
  display: grid;
  gap: 10px;
  min-width: 220px;
}

.status-chip {
  border-radius: 18px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(0, 255, 255, 0.14);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #9ef8ff;
}

.status-chip.secondary {
  color: rgba(214, 247, 255, 0.78);
}

.status-chip strong {
  color: #eefcff;
}

.section-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.rooms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.room-meta {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 255, 255, 0.14);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: rgba(214, 247, 255, 0.72);
  font-size: 12px;
}

.online-count {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.status-dot.online {
  background: #00ffff;
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.55);
}

.room-visibility {
  color: #9ef8ff;
}

.loading-state,
.empty-state {
  min-height: 220px;
  display: grid;
  place-items: center;
  text-align: center;
  color: rgba(214, 247, 255, 0.68);
}

.space-spinner {
  width: 44px;
  height: 44px;
  border: 3px solid rgba(0, 255, 255, 0.16);
  border-top-color: #00ffff;
  border-radius: 999px;
  animation: spin 1s linear infinite;
  margin: 0 auto 14px;
}

.empty-icon {
  font-family: 'Roboto Mono', 'Consolas', monospace;
  letter-spacing: 0.16em;
  font-size: 24px;
  color: #9ef8ff;
  margin-bottom: 10px;
}

.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  color: #9ef8ff;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.space-input,
.space-select {
  width: 100%;
  box-sizing: border-box;
  border-radius: 14px;
  border: 1px solid rgba(0, 255, 255, 0.14);
  background: rgba(7, 16, 34, 0.94);
  color: #eefcff;
  padding: 12px 14px;
  outline: none;
}

.space-input:focus,
.space-select:focus {
  border-color: rgba(0, 255, 255, 0.42);
  box-shadow: 0 0 0 1px rgba(0, 255, 255, 0.16), 0 0 18px rgba(0, 255, 255, 0.08);
}

.theme-selector {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.theme-btn {
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.04);
  color: #eefcff;
  cursor: pointer;
}

.theme-btn.active {
  border-color: rgba(0, 255, 255, 0.34);
  background: linear-gradient(180deg, rgba(16, 216, 255, 0.18), rgba(35, 109, 255, 0.18));
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.checkbox-label input {
  accent-color: #00ffff;
}

.error-msg {
  color: #ff9aa7;
  margin: 0;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.modal-actions > * {
  flex: 1;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Tab Bar Styles */
.tab-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 14px;
  color: rgba(222, 240, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95em;
  font-weight: 600;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(115, 224, 255, 0.3);
}

.tab-btn.active {
  background: linear-gradient(180deg, rgba(49, 120, 255, 0.25), rgba(18, 35, 78, 0.9));
  border-color: rgba(115, 224, 255, 0.4);
  color: #eef7ff;
  box-shadow: 0 4px 20px rgba(49, 120, 255, 0.2);
}

.tab-icon {
  font-size: 18px;
}

.circle-section {
  position: relative;
  z-index: 1;
  min-height: 400px;
  background: linear-gradient(180deg, rgba(14, 28, 58, 0.6), rgba(8, 16, 36, 0.8));
  border: 1px solid rgba(115, 224, 255, 0.12);
  border-radius: 20px;
  padding: 20px;
}

@media (max-width: 768px) {
  .hero-panel,
  .section-header,
  .modal-actions {
    flex-direction: column;
  }

  .hero-status {
    width: 100%;
    min-width: 0;
  }

  .theme-selector {
    grid-template-columns: 1fr;
  }
}
</style>
