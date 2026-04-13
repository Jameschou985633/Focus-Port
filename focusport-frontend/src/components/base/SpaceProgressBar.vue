<script setup>
import { computed } from 'vue'

const props = defineProps({
  progress: {
    type: Number,
    default: 0
  },
  max: {
    type: Number,
    default: 100
  },
  color: {
    type: String,
    default: 'blue'
  },
  showSegments: {
    type: Boolean,
    default: true
  },
  showText: {
    type: Boolean,
    default: true
  },
  height: {
    type: String,
    default: '24px'
  }
})

const percentage = computed(() => {
  const p = Math.max(0, Math.min(100, (props.progress / props.max) * 100))
  return Math.round(p)
})

const colorClass = computed(() => `color-${props.color}`)
</script>

<template>
  <div class="space-progress" :style="{ height }">
    <!-- Segmented progress bar -->
    <div v-if="showSegments" class="segments-container">
      <div
        v-for="i in 10"
        :key="i"
        class="segment"
        :class="[colorClass, { filled: i <= Math.floor(percentage / 10) }]"
      ></div>
    </div>

    <!-- Continuous progress bar -->
    <div v-else class="bar-container">
      <div
        class="bar-fill"
        :class="colorClass"
        :style="{ width: percentage + '%' }"
      ></div>
    </div>

    <!-- Progress text -->
    <span v-if="showText" class="progress-text">{{ percentage }}%</span>
  </div>
</template>

<style scoped>
.space-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.segments-container {
  display: flex;
  gap: 3px;
  flex: 1;
  height: 100%;
}

.segment {
  flex: 1;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 2px;
  transition: all 0.3s ease;
}

.segment.filled.color-blue {
  background: linear-gradient(180deg, #3b82f6 0%, #1e40af 100%);
  border-color: #3b82f6;
}

.segment.filled.color-green {
  background: linear-gradient(180deg, #10b981 0%, #047857 100%);
  border-color: #10b981;
}

.segment.filled.color-yellow {
  background: linear-gradient(180deg, #f59e0b 0%, #b45309 100%);
  border-color: #f59e0b;
}

.segment.filled.color-red {
  background: linear-gradient(180deg, #ef4444 0%, #b91c1c 100%);
  border-color: #ef4444;
}

.bar-container {
  flex: 1;
  height: 100%;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.bar-fill.color-blue {
  background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%);
}

.bar-fill.color-green {
  background: linear-gradient(90deg, #10b981 0%, #34d399 100%);
}

.bar-fill.color-yellow {
  background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%);
}

.bar-fill.color-red {
  background: linear-gradient(90deg, #ef4444 0%, #f87171 100%);
}

.progress-text {
  color: #3b82f6;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  font-weight: 600;
  min-width: 40px;
  text-align: right;
}
</style>
