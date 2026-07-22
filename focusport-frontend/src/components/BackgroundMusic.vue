<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const defaultTracks = [
  { name: '星际漫步', url: '/audio/space-cadet.ogg' }
]
const CUSTOM_TRACKS_KEY = 'focusport-custom-music-tracks'
const supportedAudioTypes = ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/ogg']

const isPlaying = ref(false)
const volume = ref(0.3)
const showControls = ref(false)
const audio = ref(null)
const currentTrack = ref(0)
const isShuffle = ref(false)
const isLoop = ref(true)
const customTracks = ref([])
const urlName = ref('')
const urlValue = ref('')
const fileInput = ref(null)
const objectUrls = []

const tracks = computed(() => [...defaultTracks, ...customTracks.value])
const currentName = computed(() => tracks.value[currentTrack.value]?.name || '暂无曲目')
const hasMultipleTracks = computed(() => tracks.value.length > 1)

const saveCustomTracks = () => {
  const persistentTracks = customTracks.value.filter(track => track.source === 'url')
  localStorage.setItem(CUSTOM_TRACKS_KEY, JSON.stringify(persistentTracks))
}

const loadCustomTracks = () => {
  try {
    const savedTracks = JSON.parse(localStorage.getItem(CUSTOM_TRACKS_KEY) || '[]')
    customTracks.value = Array.isArray(savedTracks)
      ? savedTracks.filter(track => track?.name && track?.url)
      : []
  } catch {
    customTracks.value = []
  }
}

const normalizeTrackName = (name, fallback) => (name || fallback).replace(/\.[^/.]+$/, '').trim()

const isSupportedAudioFile = (file) => {
  if (!file) return false
  if (supportedAudioTypes.includes(file.type)) return true
  return /\.(mp3|wav|m4a|ogg)$/i.test(file.name)
}

const playAudio = () => {
  if (!audio.value) return
  audio.value.play()
    .then(() => { isPlaying.value = true })
    .catch(() => { isPlaying.value = false })
}

const loadTrack = (index, autoplay = isPlaying.value) => {
  if (!audio.value || !tracks.value[index]) return
  audio.value.pause()
  currentTrack.value = index
  audio.value.src = tracks.value[index].url
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
    ? Math.floor(Math.random() * tracks.value.length)
    : (currentTrack.value + 1) % tracks.value.length
  loadTrack(next, true)
}

const prevTrack = () => {
  if (!hasMultipleTracks.value) {
    loadTrack(currentTrack.value, true)
    return
  }
  loadTrack((currentTrack.value - 1 + tracks.value.length) % tracks.value.length, true)
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

const addUrlTrack = () => {
  const url = urlValue.value.trim()
  if (!url) return
  const name = normalizeTrackName(urlName.value, '自定义音乐')
  customTracks.value.push({ name, url, source: 'url' })
  urlName.value = ''
  urlValue.value = ''
  saveCustomTracks()
}

const addFileTrack = (event) => {
  const files = Array.from(event.target.files || [])
  files.filter(isSupportedAudioFile).forEach((file) => {
    const url = URL.createObjectURL(file)
    objectUrls.push(url)
    customTracks.value.push({
      name: normalizeTrackName(file.name, '本地音乐'),
      url,
      source: 'file'
    })
  })
  event.target.value = ''
}

const openFilePicker = () => {
  if (fileInput.value) fileInput.value.click()
}

const removeTrack = (index) => {
  const track = tracks.value[index]
  if (!track || index < defaultTracks.length) return
  const customIndex = index - defaultTracks.length
  const [removedTrack] = customTracks.value.splice(customIndex, 1)
  if (removedTrack?.source === 'url') saveCustomTracks()
  if (removedTrack?.source === 'file') URL.revokeObjectURL(removedTrack.url)

  if (currentTrack.value === index) {
    const nextIndex = Math.min(index, tracks.value.length - 1)
    loadTrack(nextIndex, isPlaying.value)
    return
  }
  if (currentTrack.value > index) currentTrack.value -= 1
}

onMounted(() => {
  loadCustomTracks()
  audio.value = new Audio(tracks.value[0].url)
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
  objectUrls.forEach(url => URL.revokeObjectURL(url))
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

      <div class="custom-music">
        <div class="custom-title">自定义音乐</div>
        <div class="url-row">
          <input v-model="urlName" class="music-input name-input" type="text" placeholder="名称">
          <input v-model="urlValue" class="music-input" type="url" placeholder="音频链接">
          <button class="add-btn" type="button" title="添加链接" @click="addUrlTrack">+</button>
        </div>
        <div class="file-row">
          <button class="file-btn" type="button" @click="openFilePicker">选择本地音频</button>
          <input ref="fileInput" class="file-input" type="file" accept="audio/*,.mp3,.wav,.m4a,.ogg" multiple @change="addFileTrack">
        </div>
      </div>

      <div class="track-list">
        <div
          v-for="(track, index) in tracks"
          :key="track.url"
          :class="['track-item', { active: index === currentTrack, removable: index >= defaultTracks.length }]"
        >
          <button class="track-select" type="button" @click="loadTrack(index, true)">
            {{ index === currentTrack ? '♪' : '♬' }} {{ track.name }}
          </button>
          <button
            v-if="index >= defaultTracks.length"
            class="remove-track"
            type="button"
            title="移除曲目"
            @click="removeTrack(index)"
          >
            ×
          </button>
        </div>
        <div class="track-note">音频链接会保存在本机浏览器，本地文件刷新后需重新选择</div>
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
  width: min(320px, calc(100vw - 40px));
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

.custom-music {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.custom-title {
  color: rgba(222, 240, 255, 0.78);
  font-size: 12px;
  font-weight: 700;
}

.url-row {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr) 32px;
  gap: 6px;
}

.music-input {
  min-width: 0;
  height: 32px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 0 9px;
  background: rgba(255, 255, 255, 0.06);
  color: #eef7ff;
  font-size: 12px;
  outline: none;
}

.music-input::placeholder {
  color: rgba(222, 240, 255, 0.42);
}

.music-input:focus {
  border-color: rgba(74, 222, 128, 0.55);
}

.add-btn,
.file-btn {
  border: 0;
  border-radius: 8px;
  background: rgba(74, 222, 128, 0.18);
  color: #dcfce7;
  cursor: pointer;
  font-weight: 700;
}

.add-btn {
  height: 32px;
  font-size: 18px;
  line-height: 1;
}

.file-row {
  display: flex;
}

.file-btn {
  width: 100%;
  min-height: 32px;
  font-size: 12px;
}

.add-btn:hover,
.file-btn:hover {
  background: rgba(74, 222, 128, 0.3);
}

.file-input {
  display: none;
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
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(222, 240, 255, 0.7);
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: center;
  transition: all 0.15s;
}

.track-item.removable {
  grid-template-columns: minmax(0, 1fr) 28px;
}

.track-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.track-item.active {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
  font-weight: 700;
}

.track-select,
.remove-track {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.track-select {
  min-width: 0;
  padding: 7px 10px;
  overflow: hidden;
  font-size: 12px;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-track {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  font-size: 17px;
  line-height: 1;
}

.remove-track:hover {
  background: rgba(248, 113, 113, 0.16);
  color: #fecaca;
}

.track-note {
  padding: 4px 2px 0;
  color: rgba(222, 240, 255, 0.45);
  font-size: 11px;
  line-height: 1.4;
}
</style>
