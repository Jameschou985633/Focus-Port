<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const isPlaying = ref(false)
const volume = ref(0.3)
const showControls = ref(false)
const audio = ref(null)
const currentTrack = ref(0)
const isShuffle = ref(false)
const isLoop = ref(true)

const tracks = [
  { name: '星际漫步', url: '/audio/space-cadet.ogg' },
  { name: '深空漫游', url: '/audio/deep-space.ogg' },
  { name: '银河序曲', url: '/audio/galaxy-overture.ogg' },
  { name: '星辰大海', url: '/audio/starfield.ogg' }
]

const currentName = ref(tracks[0].name)

const loadTrack = (index) => {
  if (!audio.value) return
  const wasPlaying = isPlaying.value
  audio.value.pause()
  currentTrack.value = index
  audio.value.src = tracks[index].url
  currentName.value = tracks[index].name
  if (wasPlaying) {
    audio.value.play().then(() => { isPlaying.value = true }).catch(() => { isPlaying.value = false })
  }
}

const togglePlay = () => {
  if (!audio.value) return
  if (isPlaying.value) {
    audio.value.pause()
    isPlaying.value = false
  } else {
    audio.value.play().then(() => { isPlaying.value = true }).catch(() => { isPlaying.value = false })
  }
}

const nextTrack = () => {
  let next
  if (isShuffle.value) {
    next = Math.floor(Math.random() * tracks.length)
  } else {
    next = (currentTrack.value + 1) % tracks.length
  }
  loadTrack(next)
  audio.value.play().then(() => { isPlaying.value = true }).catch(() => {})
}

const prevTrack = () => {
  const prev = (currentTrack.value - 1 + tracks.length) % tracks.length
  loadTrack(prev)
  audio.value.play().then(() => { isPlaying.value = true }).catch(() => {})
}

const setVolume = (e) => {
  volume.value = parseFloat(e.target.value)
  if (audio.value) audio.value.volume = volume.value
}

const toggleControls = () => { showControls.value = !showControls.value }

const playCurrentTrack = () => {
  if (!audio.value) return
  audio.value.play().then(() => { isPlaying.value = true }).catch(() => { isPlaying.value = false })
}
const toggleShuffle = () => { isShuffle.value = !isShuffle.value }
const toggleLoop = () => {
  isLoop.value = !isLoop.value
  if (audio.value) audio.value.loop = isLoop.value
}

onMounted(() => {
  audio.value = new Audio(tracks[0].url)
  audio.value.loop = true
  audio.value.volume = volume.value
  audio.value.addEventListener('ended', () => {
    if (!isLoop.value) nextTrack()
  })
  audio.value.play().then(() => { isPlaying.value = true }).catch(() => { isPlaying.value = false })
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
      <div class="track-name">{{ currentName }}</div>

      <div class="transport-row">
        <button class="ctrl-btn" @click="toggleShuffle" :class="{ active: isShuffle }" title="随机">🔀</button>
        <button class="ctrl-btn" @click="prevTrack" title="上一首">⏮</button>
        <button class="play-btn" @click="togglePlay">
          {{ isPlaying ? '⏸️' : '▶️' }}
        </button>
        <button class="ctrl-btn" @click="nextTrack" title="下一首">⏭</button>
        <button class="ctrl-btn" @click="toggleLoop" :class="{ active: isLoop }" title="单曲循环">🔁</button>
      </div>

      <div class="volume-row">
        <span class="vol-icon">🔈</span>
        <input type="range" min="0" max="1" step="0.05" :value="volume" @input="setVolume" class="volume-slider" />
        <span class="vol-icon">🔊</span>
      </div>

      <div class="track-list">
        <button
          v-for="(track, idx) in tracks"
          :key="idx"
          :class="['track-item', { active: idx === currentTrack }]"
          @click="loadTrack(idx); playCurrentTrack()"
        >
          {{ idx === currentTrack ? '♫' : '♪' }} {{ track.name }}
        </button>
      </div>
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
  width: 44px; height: 44px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.2);
  border: 2px solid rgba(59, 130, 246, 0.5);
  font-size: 20px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex; align-items: center; justify-content: center;
}

.music-btn:hover { background: rgba(59, 130, 246, 0.4); transform: scale(1.1); }
.music-btn.playing { animation: pulse-music 2s infinite; }

@keyframes pulse-music {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.music-controls {
  background: rgba(15, 23, 42, 0.96);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  backdrop-filter: blur(12px);
  min-width: 200px;
}

.track-name {
  font-size: 13px;
  font-weight: 600;
  color: #eef7ff;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.transport-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.ctrl-btn {
  width: 30px; height: 30px;
  border-radius: 8px;
  background: rgba(255,255,255,0.05);
  border: none;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex; align-items: center; justify-content: center;
}

.ctrl-btn:hover { background: rgba(255,255,255,0.1); }
.ctrl-btn.active { background: rgba(59,130,246,0.2); }

.play-btn {
  width: 36px; height: 36px;
  border-radius: 8px;
  background: rgba(74, 222, 128, 0.2);
  border: 1px solid rgba(74, 222, 128, 0.4);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex; align-items: center; justify-content: center;
}

.play-btn:hover { background: rgba(74, 222, 128, 0.4); }

.volume-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.vol-icon { font-size: 12px; }

.volume-slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  outline: none;
}

.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px; height: 14px;
  background: #4ade80;
  border-radius: 50%;
  cursor: pointer;
}

.track-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 120px;
  overflow-y: auto;
}

.track-item {
  width: 100%;
  padding: 6px 10px;
  background: rgba(255,255,255,0.04);
  border: none;
  border-radius: 8px;
  color: rgba(222,240,255,0.7);
  font-size: 12px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}

.track-item:hover { background: rgba(255,255,255,0.08); }
.track-item.active { background: rgba(59,130,246,0.15); color: #93c5fd; font-weight: 600; }
</style>
