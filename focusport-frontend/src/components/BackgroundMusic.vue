<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const tracks = [
  { name: '星际漫步', url: '/audio/space-cadet.ogg' }
]

const isPlaying = ref(false)
const volume = ref(0.3)
const showControls = ref(false)
const audio = ref(null)
const currentTrack = ref(0)
const isShuffle = ref(false)
const isLoop = ref(true)

const currentName = computed(() => tracks[currentTrack.value]?.name || '暂无曲目')
const hasMultipleTracks = computed(() => tracks.length > 1)

const playAudio = () => {
  if (!audio.value) return
  audio.value.play()
    .then(() => { isPlaying.value = true })
    .catch(() => { isPlaying.value = false })
}

const loadTrack = (index, autoplay = isPlaying.value) => {
  if (!audio.value || !tracks[index]) return
  audio.value.pause()
  currentTrack.value = index
  audio.value.src = tracks[index].url
  audio.value.load()
  if (autoplay) playAudio()
  else isPlaying.value = false
}

const togglePlay = () => {
  if (!audio.value) return
  if (isPlaying.value) {
    audio.value.pause()
    isPlaying.value = false
    return
  }
  playAudio()
}

const nextTrack = () => {
  if (!hasMultipleTracks.value) {
    loadTrack(currentTrack.value, true)
    return
  }
  const next = isShuffle.value
    ? Math.floor(Math.random() * tracks.length)
    : (currentTrack.value + 1) % tracks.length
  loadTrack(next, true)
}

const prevTrack = () => {
  if (!hasMultipleTracks.value) {
    loadTrack(currentTrack.value, true)
    return
  }
  loadTrack((currentTrack.value - 1 + tracks.length) % tracks.length, true)
}

const setVolume = (event) => {
  volume.value = parseFloat(event.target.value)
  if (audio.value) audio.value.volume = volume.value
}

const toggleControls = () => {
  showControls.value = !showControls.value
}

const toggleShuffle = () => {
  if (!hasMultipleTracks.value) return
  isShuffle.value = !isShuffle.value
}

const toggleLoop = () => {
  isLoop.value = !isLoop.value
  if (audio.value) audio.value.loop = isLoop.value
}

onMounted(() => {
  audio.value = new Audio(tracks[0].url)
  audio.value.loop = isLoop.value
  audio.value.volume = volume.value
  audio.value.addEventListener('ended', () => {
    if (!isLoop.value) nextTrack()
  })
  playAudio()
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
    <button class="music-btn" :class="{ playing: isPlaying }" type="button" @click="toggleControls">
      <span v-if="isPlaying">♪</span>
      <span v-else>♫</span>
    </button>

    <div v-if="showControls" class="music-controls">
      <div class="track-name">{{ currentName }}</div>

      <div class="transport-row">
        <button class="ctrl-btn" :class="{ active: isShuffle }" :disabled="!hasMultipleTracks" title="随机播放" type="button" @click="toggleShuffle">↝</button>
        <button class="ctrl-btn" title="上一首" type="button" @click="prevTrack">◀◀</button>
        <button class="play-btn" type="button" @click="togglePlay">
          {{ isPlaying ? 'Ⅱ' : '▶' }}
        </button>
        <button class="ctrl-btn" title="下一首" type="button" @click="nextTrack">▶▶</button>
        <button class="ctrl-btn" :class="{ active: isLoop }" title="循环播放" type="button" @click="toggleLoop">↻</button>
      </div>

      <div class="volume-row">
        <span class="vol-icon">低</span>
        <input class="volume-slider" type="range" min="0" max="1" step="0.05" :value="volume" @input="setVolume">
        <span class="vol-icon">高</span>
      </div>

      <div class="track-list">
        <button
          v-for="(track, index) in tracks"
          :key="track.url"
          :class="['track-item', { active: index === currentTrack }]"
          type="button"
          @click="loadTrack(index, true)"
        >
          {{ index === currentTrack ? '♪' : '♬' }} {{ track.name }}
        </button>
        <div class="track-note">已隐藏未找到音频文件的曲目</div>
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
  width: 44px;
  height: 44px;
  border: 2px solid rgba(59, 130, 246, 0.5);
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.2);
  color: white;
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
  min-width: 220px;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  padding: 14px;
  background: rgba(15, 23, 42, 0.96);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.track-name {
  color: #eef7ff;
  font-size: 13px;
  font-weight: 700;
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

.ctrl-btn,
.play-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  cursor: pointer;
  transition: all 0.15s;
}

.ctrl-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: white;
  font-size: 12px;
}

.ctrl-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.ctrl-btn.active {
  background: rgba(59, 130, 246, 0.2);
}

.ctrl-btn:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}

.play-btn {
  width: 38px;
  height: 38px;
  border: 1px solid rgba(74, 222, 128, 0.4);
  border-radius: 10px;
  background: rgba(74, 222, 128, 0.2);
  color: white;
  font-size: 16px;
}

.play-btn:hover {
  background: rgba(74, 222, 128, 0.4);
}

.volume-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.vol-icon {
  color: rgba(222, 240, 255, 0.74);
  font-size: 11px;
}

.volume-slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  outline: none;
}

.volume-slider::-webkit-slider-thumb {
  width: 14px;
  height: 14px;
  -webkit-appearance: none;
  border-radius: 50%;
  background: #4ade80;
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
  border: 0;
  border-radius: 8px;
  padding: 7px 10px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(222, 240, 255, 0.7);
  font-size: 12px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}

.track-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.track-item.active {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
  font-weight: 700;
}

.track-note {
  padding: 4px 2px 0;
  color: rgba(222, 240, 255, 0.45);
  font-size: 11px;
  line-height: 1.4;
}
</style>
