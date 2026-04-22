<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  visible: { type: Boolean, default: false },
  username: { type: String, default: '' }
})

const emit = defineEmits(['complete', 'done'])

const isVisible = computed(() => props.show || props.visible)
const isMounted = ref(false)
const phase = ref('idle')

let timers = []

const clearTimers = () => {
  timers.forEach((timer) => clearTimeout(timer))
  timers = []
}

const queue = (callback, delay) => {
  const timer = setTimeout(callback, delay)
  timers.push(timer)
}

const startFlight = () => {
  clearTimers()
  isMounted.value = true
  phase.value = 'verify'

  queue(() => { phase.value = 'expand' }, 360)
  queue(() => { phase.value = 'ascent' }, 1080)
  queue(() => { phase.value = 'arrive' }, 2450)
  queue(() => {
    emit('complete')
    emit('done')
  }, 3300)
}

watch(isVisible, (value) => {
  if (value) {
    startFlight()
    return
  }

  clearTimers()
  phase.value = 'idle'
  isMounted.value = false
})

onUnmounted(() => {
  clearTimers()
})
</script>

<template>
  <div v-if="isMounted" class="login-flight-overlay" :class="phase" aria-live="polite">
    <div class="flight-scene">
      <div class="flight-image"></div>
      <div class="flight-atmosphere"></div>
      <div class="flight-grid"></div>
      <div class="flight-streaks">
        <span v-for="index in 14" :key="index"></span>
      </div>
    </div>

    <div class="launch-copy">
      <strong>下一站<br>专注星港</strong>
    </div>
  </div>
</template>

<style scoped>
.login-flight-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  overflow: hidden;
  color: #f7fbff;
  pointer-events: all;
  background: #020513;
  font-family: "Plus Jakarta Sans", "Noto Sans SC", "Microsoft YaHei", sans-serif;
  opacity: 0;
  animation: overlayFadeIn 260ms ease forwards;
}

.flight-scene,
.flight-image,
.flight-atmosphere,
.flight-grid,
.flight-streaks {
  position: absolute;
  inset: 0;
}

.flight-scene {
  overflow: hidden;
  transform-origin: center bottom;
}

.flight-image {
  background:
    linear-gradient(180deg, rgba(3, 7, 22, 0.08), rgba(3, 7, 22, 0.36) 58%, rgba(3, 7, 22, 0.78)),
    linear-gradient(90deg, rgba(3, 7, 22, 0.28), rgba(3, 7, 22, 0.02) 44%, rgba(3, 7, 22, 0.32)),
    url('/assets/login-vision-bg.png') center / cover no-repeat,
    radial-gradient(circle at 45% 35%, rgba(72, 128, 255, 0.45), transparent 36%),
    linear-gradient(135deg, #152058, #030615 76%);
  transform: scale(1.02);
  transform-origin: center bottom;
  clip-path: inset(0 48% 0 0 round 0);
  filter: saturate(1.08) contrast(1.06);
  animation: imageExpand 900ms cubic-bezier(0.19, 1, 0.22, 1) forwards;
}

.flight-atmosphere {
  background:
    radial-gradient(circle at 50% 68%, rgba(72, 128, 255, 0.32), transparent 34%),
    radial-gradient(circle at 52% 8%, rgba(72, 221, 255, 0.34), transparent 26%),
    linear-gradient(0deg, rgba(2, 5, 19, 0.76), transparent 54%);
  mix-blend-mode: screen;
  opacity: 0.66;
}

.flight-grid {
  background-image:
    linear-gradient(rgba(180, 223, 255, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(180, 223, 255, 0.08) 1px, transparent 1px);
  background-size: 72px 72px;
  opacity: 0.24;
  mask-image: linear-gradient(0deg, rgba(0, 0, 0, 0.88), transparent 78%);
  transform-origin: center bottom;
}

.flight-streaks {
  opacity: 0;
  transform: perspective(900px) rotateX(62deg) translateY(18vh);
}

.flight-streaks span {
  position: absolute;
  bottom: -24vh;
  width: 2px;
  height: 34vh;
  border-radius: 999px;
  background: linear-gradient(180deg, transparent, rgba(197, 238, 255, 0.92), transparent);
  box-shadow: 0 0 24px rgba(72, 209, 255, 0.55);
  animation: lightRush 780ms linear infinite;
}

.flight-streaks span:nth-child(1) { left: 8%; animation-delay: -0.12s; }
.flight-streaks span:nth-child(2) { left: 14%; animation-delay: -0.42s; height: 44vh; }
.flight-streaks span:nth-child(3) { left: 22%; animation-delay: -0.24s; }
.flight-streaks span:nth-child(4) { left: 31%; animation-delay: -0.64s; height: 48vh; }
.flight-streaks span:nth-child(5) { left: 39%; animation-delay: -0.18s; }
.flight-streaks span:nth-child(6) { left: 48%; animation-delay: -0.72s; height: 42vh; }
.flight-streaks span:nth-child(7) { left: 56%; animation-delay: -0.36s; }
.flight-streaks span:nth-child(8) { left: 64%; animation-delay: -0.54s; height: 50vh; }
.flight-streaks span:nth-child(9) { left: 72%; animation-delay: -0.2s; }
.flight-streaks span:nth-child(10) { left: 80%; animation-delay: -0.68s; height: 46vh; }
.flight-streaks span:nth-child(11) { left: 88%; animation-delay: -0.3s; }
.flight-streaks span:nth-child(12) { left: 95%; animation-delay: -0.5s; height: 40vh; }
.flight-streaks span:nth-child(13) { left: 3%; animation-delay: -0.76s; }
.flight-streaks span:nth-child(14) { left: 68%; animation-delay: -0.08s; }

.launch-copy {
  position: absolute;
  left: clamp(24px, 6vw, 88px);
  bottom: clamp(34px, 8vh, 92px);
  z-index: 3;
  opacity: 0;
  transform: translateY(24px);
}

.launch-copy strong {
  color: #ffffff;
  font-size: clamp(40px, 7vw, 92px);
  line-height: 1.05;
  font-weight: 950;
  letter-spacing: -0.08em;
}

.login-flight-overlay.expand .launch-copy,
.login-flight-overlay.ascent .launch-copy,
.login-flight-overlay.arrive .launch-copy {
  animation: copyIn 620ms cubic-bezier(0.19, 1, 0.22, 1) forwards;
}

.login-flight-overlay.ascent .flight-scene,
.login-flight-overlay.arrive .flight-scene {
  animation: cameraAscent 1650ms cubic-bezier(0.11, 0.76, 0.22, 1) forwards;
}

.login-flight-overlay.ascent .flight-grid,
.login-flight-overlay.arrive .flight-grid {
  animation: gridDrop 900ms linear infinite;
}

.login-flight-overlay.ascent .flight-streaks,
.login-flight-overlay.arrive .flight-streaks {
  opacity: 0.92;
  transition: opacity 220ms ease;
}

.login-flight-overlay.arrive::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 4;
  background: radial-gradient(circle at 50% 20%, rgba(228, 247, 255, 0.96), rgba(84, 159, 255, 0.38) 34%, rgba(2, 5, 19, 0.8) 72%);
  opacity: 0;
  animation: portalFlash 800ms ease forwards;
}

@keyframes overlayFadeIn {
  to { opacity: 1; }
}

@keyframes imageExpand {
  0% {
    clip-path: inset(0 48% 0 0 round 0);
    transform: translateX(-3vw) scale(1.02);
  }
  100% {
    clip-path: inset(0 0 0 0 round 0);
    transform: translateX(0) scale(1.04);
  }
}

@keyframes copyIn {
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes cameraAscent {
  0% {
    transform: translateY(0) scale(1);
    filter: blur(0);
  }
  58% {
    transform: translateY(-18vh) scale(1.16);
    filter: blur(0.4px);
  }
  100% {
    transform: translateY(-38vh) scale(1.34);
    filter: blur(1.1px);
  }
}

@keyframes gridDrop {
  from { background-position: 0 0, 0 0; }
  to { background-position: 0 144px, 0 144px; }
}

@keyframes lightRush {
  from { transform: translateY(0) scaleY(0.55); opacity: 0; }
  24% { opacity: 0.98; }
  to { transform: translateY(-118vh) scaleY(1.35); opacity: 0; }
}

@keyframes portalFlash {
  0% { opacity: 0; transform: scale(0.94); }
  45% { opacity: 0.82; transform: scale(1.02); }
  100% { opacity: 1; transform: scale(1.08); }
}

@media (max-width: 640px) {
  .launch-copy {
    right: 22px;
    bottom: 34px;
  }

  .launch-copy strong {
    font-size: 42px;
  }
}
</style>
