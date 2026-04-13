<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['done'])

const SCRIPTS = [
  // 方案一：硬核指令流
  { lines: ['身份验证通过。准许接入 FocusPort。'], style: 'command' },
  // 方案二：星际拓荒流
  { lines: ['正在脱离现实引力', '跃迁至专注视界。'], style: 'warp' },
  // 方案三：极客自律流
  { lines: ['正在过滤信息碎片...', '正在重构时间线...', '绝对专注区已展开。'], style: 'focus' },
  // 方案四：极简科幻
  { lines: ['FOCUS PORT : ONLINE'], style: 'minimal' }
]

const displayedLines = ref([])
const currentLineIdx = ref(0)
const currentCharIdx = ref(0)
const isTyping = ref(false)
const cursorVisible = ref(true)
const activeStyle = ref('command')

let typeTimer = null
let lineTimer = null
let doneTimer = null
let blinkTimer = null

watch(() => props.visible, (v) => {
  if (!v) return

  const script = SCRIPTS[Math.floor(Math.random() * SCRIPTS.length)]
  activeStyle.value = script.style
  displayedLines.value = []
  currentLineIdx.value = 0
  currentCharIdx.value = 0
  isTyping.value = true
  cursorVisible.value = true

  startBlink()
  typeLine(script.lines, 0)
})

const startBlink = () => {
  if (blinkTimer) clearInterval(blinkTimer)
  blinkTimer = setInterval(() => {
    cursorVisible.value = !cursorVisible.value
  }, 530)
}

const typeLine = (lines, lineIdx) => {
  if (lineIdx >= lines.length) {
    isTyping.value = false
    doneTimer = setTimeout(() => {
      clearInterval(blinkTimer)
      emit('done')
    }, 600)
    return
  }

  displayedLines.value.push('')
  currentLineIdx.value = lineIdx
  currentCharIdx.value = 0

  const text = lines[lineIdx]
  const speed = activeStyle.value === 'minimal' ? 60 : 45

  typeTimer = setInterval(() => {
    if (currentCharIdx.value < text.length) {
      const ci = currentCharIdx.value
      displayedLines.value.splice(lineIdx, 1, text.slice(0, ci + 1))
      currentCharIdx.value++
    } else {
      clearInterval(typeTimer)
      lineTimer = setTimeout(() => typeLine(lines, lineIdx + 1), 320)
    }
  }, speed)
}

onUnmounted(() => {
  clearInterval(typeTimer)
  clearTimeout(lineTimer)
  clearTimeout(doneTimer)
  clearInterval(blinkTimer)
})
</script>

<template>
  <div v-if="visible" class="login-overlay" :class="activeStyle">
    <div class="pixel-grid"></div>
    <div class="scan-lines"></div>
    <div class="terminal-area">
      <span v-if="activeStyle !== 'minimal'" class="eyebrow">SYSTEM INIT</span>
      <div class="lines">
        <p v-for="(line, i) in displayedLines" :key="i" class="type-line">
          <span>{{ line }}</span>
          <span v-if="i === currentLineIdx && isTyping && cursorVisible" class="cursor">_</span>
        </p>
      </div>
      <span v-if="!isTyping && cursorVisible && activeStyle !== 'minimal'" class="cursor final-cursor">_</span>
    </div>
  </div>
</template>

<style scoped>
.login-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  overflow: hidden;
  pointer-events: all;
  background:
    radial-gradient(circle at 50% 50%, rgba(47, 216, 255, 0.15), transparent 30%),
    linear-gradient(180deg, rgba(6, 14, 30, 0.92), rgba(6, 14, 30, 0.98)),
    #040a18;
  display: grid;
  place-items: center;
  animation: overlayIn 300ms ease forwards;
}

.pixel-grid,
.scan-lines {
  position: absolute;
  inset: 0;
}

.pixel-grid {
  background-image:
    linear-gradient(rgba(115, 224, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(115, 224, 255, 0.08) 1px, transparent 1px);
  background-size: 22px 22px;
  transform: scale(1.1);
  opacity: 0.4;
}

.scan-lines {
  background: repeating-linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.06) 0,
    rgba(255, 255, 255, 0.06) 1px,
    transparent 1px,
    transparent 6px
  );
  mix-blend-mode: screen;
  animation: scanDrift 1.8s linear infinite;
}

.terminal-area {
  position: relative;
  z-index: 1;
  text-align: left;
  max-width: min(560px, 85vw);
  font-family: 'Roboto Mono', 'Consolas', 'Courier New', monospace;
}

.eyebrow {
  display: block;
  margin-bottom: 14px;
  font-size: 11px;
  letter-spacing: 0.28em;
  color: rgba(156, 230, 255, 0.72);
  text-transform: uppercase;
}

.lines {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.type-line {
  margin: 0;
  font-size: clamp(16px, 2.8vw, 22px);
  color: #c8eeff;
  line-height: 1.5;
  letter-spacing: 0.02em;
}

.cursor {
  color: #5ce3ff;
  animation: blink 530ms step-end infinite;
}

.final-cursor {
  margin-top: 12px;
  display: inline-block;
  font-size: 18px;
}

/* Minimal style overrides */
.login-overlay.minimal .type-line {
  font-size: clamp(28px, 5vw, 48px);
  font-weight: 900;
  letter-spacing: 0.12em;
  text-align: center;
  color: #5ce3ff;
  text-shadow: 0 0 32px rgba(92, 227, 255, 0.3);
}

.login-overlay.minimal .lines {
  align-items: center;
}

/* Warp style - slightly different tint */
.login-overlay.warp {
  background:
    radial-gradient(circle at 50% 60%, rgba(109, 92, 255, 0.18), transparent 35%),
    linear-gradient(180deg, rgba(10, 16, 40, 0.92), rgba(6, 10, 24, 0.98)),
    #050a1a;
}

/* Focus style - green tint */
.login-overlay.focus .pixel-grid {
  background-image:
    linear-gradient(rgba(99, 255, 173, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 255, 173, 0.06) 1px, transparent 1px);
}

.login-overlay.focus .type-line {
  color: #a0ffd8;
}

@keyframes overlayIn {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

@keyframes scanDrift {
  0% { transform: translateY(-6px); }
  100% { transform: translateY(6px); }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
