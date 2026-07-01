<script setup>
import { ref, onMounted } from 'vue'

const settings = ref({
  focusReminder: true,
  breakReminder: true,
  taskDeadline: true,
  soundEffect: 'standard',
  browserNotification: false
})

const soundOptions = [
  { value: 'none', label: '静音', desc: '不播放提示音' },
  { value: 'soft', label: '轻柔', desc: '柔和提示音' },
  { value: 'standard', label: '标准', desc: '默认提示音' },
  { value: 'strong', label: '强烈', desc: '更醒目的提示音' }
]

function loadSettings() {
  const saved = localStorage.getItem('notificationSettings')
  if (!saved) return
  try {
    settings.value = { ...settings.value, ...JSON.parse(saved) }
  } catch (e) {
    console.error('Failed to load notification settings:', e)
  }
}

function saveSettings() {
  localStorage.setItem('notificationSettings', JSON.stringify(settings.value))
}

async function requestBrowserNotification() {
  if (!('Notification' in window)) {
    alert('当前浏览器不支持系统通知')
    return
  }

  if (Notification.permission === 'granted') {
    settings.value.browserNotification = true
    saveSettings()
    return
  }

  const permission = await Notification.requestPermission()
  if (permission === 'granted') {
    settings.value.browserNotification = true
    saveSettings()
    new Notification('FocusPort', { body: '通知权限已开启！' })
  } else {
    settings.value.browserNotification = false
    alert('通知权限被拒绝，请在浏览器设置中手动开启')
  }
}

function toggleBrowserNotification() {
  if (settings.value.browserNotification) {
    requestBrowserNotification()
  } else {
    saveSettings()
  }
}

function updateSetting(key, value) {
  settings.value[key] = value
  saveSettings()
}

onMounted(loadSettings)
</script>

<template>
  <section class="notification-settings">
    <header class="section-header">
      <p class="section-kicker">NOTIFICATION</p>
      <h3>通知设置</h3>
    </header>

    <div class="settings-list">
      <div class="setting-item">
        <div class="setting-info">
          <span class="setting-label">专注提醒</span>
          <span class="setting-desc">开始与结束专注时发送提示</span>
        </div>
        <label class="toggle-switch">
          <input v-model="settings.focusReminder" type="checkbox" @change="saveSettings" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="setting-item">
        <div class="setting-info">
          <span class="setting-label">休息提醒</span>
          <span class="setting-desc">长时间专注后提醒休息</span>
        </div>
        <label class="toggle-switch">
          <input v-model="settings.breakReminder" type="checkbox" @change="saveSettings" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="setting-item">
        <div class="setting-info">
          <span class="setting-label">任务截止提醒</span>
          <span class="setting-desc">任务到期前发送提示</span>
        </div>
        <label class="toggle-switch">
          <input v-model="settings.taskDeadline" type="checkbox" @change="saveSettings" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="setting-item">
        <div class="setting-info">
          <span class="setting-label">浏览器通知</span>
          <span class="setting-desc">允许系统级推送通知</span>
        </div>
        <label class="toggle-switch">
          <input v-model="settings.browserNotification" type="checkbox" @change="toggleBrowserNotification" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="setting-item sound-setting">
        <div class="setting-info">
          <span class="setting-label">提醒音效</span>
          <span class="setting-desc">选择提示声音风格</span>
        </div>
        <div class="sound-options">
          <button
            v-for="opt in soundOptions"
            :key="opt.value"
            type="button"
            :class="['sound-btn', { active: settings.soundEffect === opt.value }]"
            @click="updateSetting('soundEffect', opt.value)"
          >
            <span class="sound-label">{{ opt.label }}</span>
            <span class="sound-desc">{{ opt.desc }}</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.notification-settings {
  padding: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 20px;
}

.section-header {
  margin-bottom: 16px;
}

.section-kicker {
  margin: 0 0 4px;
  font-size: 10px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: rgba(156, 223, 255, 0.6);
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  color: #eef7ff;
}

.settings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(115, 224, 255, 0.1);
  border-radius: 14px;
}

.setting-info {
  flex: 1;
  min-width: 0;
}

.setting-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #eef7ff;
}

.setting-desc {
  display: block;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.6);
  margin-top: 2px;
}

.toggle-switch {
  position: relative;
  width: 48px;
  height: 26px;
  flex-shrink: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  transition: background 0.2s ease;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  left: 3px;
  top: 3px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s ease;
}

.toggle-switch input:checked + .toggle-slider {
  background: linear-gradient(135deg, #22d3ee, #3b82f6);
}

.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(22px);
}

.sound-setting {
  align-items: flex-start;
}

.sound-options {
  width: 100%;
  display: grid;
  gap: 8px;
}

.sound-btn {
  border: 1px solid rgba(115, 224, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #eef7ff;
  border-radius: 12px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
}

.sound-btn.active {
  border-color: rgba(56, 189, 248, 0.55);
  background: rgba(56, 189, 248, 0.12);
}

.sound-label {
  display: block;
  font-weight: 700;
}

.sound-desc {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: rgba(222, 240, 255, 0.68);
}
</style>
