<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const isPlaying = ref(false)
const volume = ref(0.3)
const showControls = ref(false)
const audio = ref(null)

const togglePlay = () => {
  if (!audio.value) return

  if (isPlaying.value) {
    audio.value.pause()
  } else {
    audio.value.play()
  }
  isPlaying.value = !isPlaying.value
}

const setVolume = (e) => {
  volume.value = parseFloat(e.target.value)
  if (audio.value) {
    audio.value.volume = volume.value
  }
}

const toggleControls = () => {
  showControls.value = !showControls.value
}

onMounted(() => {
  audio.value = new Audio('/audio/space-cadet.ogg')
  audio.value.loop = true
  audio.value.volume = volume.value

  // 尝试自动播放（可能被浏览器阻止）
  audio.value.play().then(() => {
    isPlaying.value = true
  }).catch(() => {
    // 浏览器阻止自动播放，需要用户手动点击
    isPlaying.value = false
  })
})

onUnmounted(() => {
  if (audio.value) {
    audio.value.pause()
    audio.value = null
  }
})
</script>

<template>
  <div class="music-player">
    <button class="music-btn" @click="toggleControls" :class="{ playing: isPlaying }">
      <span v-if="isPlaying">🎵</span>
      <span v-else>🔇</span>
    </button>

    <div v-if="showControls" class="music-controls">
      <button class="play-btn" @click="togglePlay">
        {{ isPlaying ? '⏸️' : '▶️' }}
      </button>
      <input
        type="range"
        min="0"
        max="1"
        step="0.1"
        :value="volume"
        @input="setVolume"
        class="volume-slider"
      />
    </div>
  </div>
</template>

<style scoped>
.music-player {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.music-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.2);
  border: 2px solid rgba(59, 130, 246, 0.5);
  font-size: 20px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-btn:hover {
  background: rgba(59, 130, 246, 0.4);
  transform: scale(1.1);
}

.music-btn.playing {
  animation: pulse-music 2s infinite;
}

@keyframes pulse-music {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.music-controls {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  backdrop-filter: blur(10px);
}

.play-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(74, 222, 128, 0.2);
  border: 1px solid rgba(74, 222, 128, 0.4);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.play-btn:hover {
  background: rgba(74, 222, 128, 0.4);
}

.volume-slider {
  width: 80px;
  height: 6px;
  -webkit-appearance: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  outline: none;
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  background: #4ade80;
  border-radius: 50%;
  cursor: pointer;
}
</style>
