<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  formattedTime: {
    type: String,
    required: true
  },
  isRunning: {
    type: Boolean,
    default: false
  },
  focusProgress: {
    type: Number,
    default: 0
  },
  plantedCount: {
    type: Number,
    default: 0
  },
  durationOptions: {
    type: Array,
    default: () => [15, 25, 30, 45, 60]
  },
  selectedDuration: {
    type: Number,
    default: 25
  }
})

const emit = defineEmits(['start-focus', 'change-duration'])

// 折叠状态
const isCollapsed = ref(true)

// 当前阶段文字
const phaseText = computed(() => {
  if (props.focusProgress < 0.5) return '白天'
  if (props.focusProgress < 1) return '黄昏'
  return '夜晚'
})
</script>

<template>
  <!-- 折叠状态 - 小药丸按钮 -->
  <div v-if="isCollapsed" class="collapsed-pill" @click="isCollapsed = false">
    <span class="pill-icon">🍅</span>
    <span class="pill-time">{{ formattedTime }}</span>
    <span class="pill-expand">▼</span>
  </div>

  <!-- 展开状态 - 完整面板 -->
  <div v-else class="pomodoro-container">
    <!-- 收起按钮 -->
    <button class="collapse-btn" @click="isCollapsed = true">▲ 收起</button>

    <!-- 时长选择器 -->
    <div class="duration-selector">
      <button
        v-for="min in durationOptions"
        :key="min"
        :class="['duration-btn', { active: selectedDuration === min }]"
        :disabled="isRunning"
        @click="emit('change-duration', min)"
      >
        {{ min }}分
      </button>
    </div>

    <!-- 极简高级的数字倒计时 -->
    <p class="time-display">{{ formattedTime }}</p>

    <!-- 状态文字 -->
    <p class="status-text">{{ phaseText }} · 已种植 {{ plantedCount }} 棵</p>

    <!-- 现代感胶囊按钮 -->
    <button
      class="action-btn"
      :disabled="isRunning"
      @click="emit('start-focus')"
    >
      {{ isRunning ? '专注中...' : '开始专注' }}
    </button>
  </div>
</template>

<style scoped>
/* 折叠状态 - 小药丸 */
.collapsed-pill {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;

  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 50px;

  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

  cursor: pointer;
  transition: all 0.3s ease;
}

.collapsed-pill:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateX(-50%) translateY(-2px);
}

.pill-icon {
  font-size: 18px;
}

.pill-time {
  font-size: 16px;
  font-weight: 700;
  color: white;
  font-family: 'SF Mono', 'Monaco', monospace;
  letter-spacing: 1px;
}

.pill-expand {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
  transition: transform 0.3s;
}

.collapsed-pill:hover .pill-expand {
  transform: translateY(2px);
}

/* 悬浮毛玻璃容器 */
.pomodoro-container {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;

  width: 300px;
  padding: 20px 30px 24px;
  border-radius: 24px;

  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);

  display: flex;
  flex-direction: column;
  align-items: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;

  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

/* 收起按钮 */
.collapse-btn {
  position: absolute;
  top: 8px;
  right: 12px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: all 0.2s;
}

.collapse-btn:hover {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.1);
}

/* 时长选择器 */
.duration-selector {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  margin-top: 8px;
}

.duration-btn {
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.duration-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.9);
}

.duration-btn.active {
  background: rgba(255, 255, 255, 0.3);
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.5);
}

.duration-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 极简高级的数字倒计时 */
.time-display {
  font-size: 54px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 2px;
  margin: 0 0 10px 0;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 状态文字 */
.status-text {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 20px;
}

/* 现代感胶囊按钮 */
.action-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.5);
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  padding: 12px 36px;
  border-radius: 50px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.action-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.action-btn:active:not(:disabled) {
  transform: translateY(0);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
