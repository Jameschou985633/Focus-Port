<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'

import TopStatusBar from './TopStatusBar.vue'
import LeftSidebar from './LeftSidebar.vue'
import RightSidebar from './RightSidebar.vue'
import TopActionBar from './TopActionBar.vue'
import MobileNav from './layout/MobileNav.vue'
import CityModelInstance from './CityModelInstance.vue'
import FloatingIsland from './FloatingIsland.vue'
import PlacedModel from './PlacedModel.vue'
import DockWindow from './dock/DockWindow.vue'
import AIAssistantDock from './dock/AIAssistantDock.vue'
import { focusApi, unifiedShopApi } from '../api'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'
import { useMasterTimelineStore } from '../stores/masterTimeline'
import { useFocusHubStore } from '../stores/focusHub'
import '../assets/kenney-ui/kenney-hud.css'

const props = defineProps({
  previewMode: {
    type: Boolean,
    default: false
  }
})

const router = useRouter()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()
const masterTimelineStore = useMasterTimelineStore()
const focusHubStore = useFocusHubStore()
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const currentUsername = ref(localStorage.getItem('username') || 'guest')

const citySlots = ref([])
const placedDecorations = ref([])
const selectedDecoration = ref(null)
const placementItem = ref(null)
const isPlacementMode = ref(false)
const isPlacementSubmitting = ref(false)
const hoveredPlacementSlotId = ref('')
const supportsHover = ref(false)

const showAiWindow = ref(false)

const userGrowth = ref({
  exp: 0,
  level: 1,
  streak_days: 0,
  discipline_score: 50,
  focus_energy: 0,
  total_focus_minutes: 0
})

const durationOptions = [15, 25, 30, 45, 60]
const showFocusDebrief = ref(false)
const focusSessionLog = ref('')
const isFocusSettlementSubmitting = ref(false)
const pendingFocusDuration = ref(0)
const focusSettlementResult = ref(null)
const showFocusRewardModal = ref(false)
const terminalFeed = ref(null)
let focusRewardTimer = null

const CITY_THEME = {
  sky: '#050914',
  ambient: '#80d2ff',
  ambientIntensity: 1.15,
  directional: '#78b4ff',
  directionalIntensity: 1.55,
  fogPlane: '#0b1022',
  horizonGlow: '#6d5cff'
}

const SAFE_CITY_Y = 1.7

const formattedTime = computed(() => {
  const total = Math.max(0, focusHubStore.pomodoro.remainingSeconds)
  const mins = Math.floor(total / 60)
  const secs = total % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
})

const focusProgress = computed(() => {
  const total = focusHubStore.pomodoro.focusMinutes * 60
  return total > 0 ? 1 - focusHubStore.pomodoro.remainingSeconds / total : 0
})

const focusMinutes = computed(() => userGrowth.value.total_focus_minutes || 0)
const selectedDifficultyMeta = computed(() => (
  focusHubStore.pomodoro.taskDifficulty === 'L2'
    ? {
        label: 'High / L2',
        multiplier: '1.5x',
        description: '硬核刷题、写代码、深度复习'
      }
    : {
        label: 'Low / L1',
        multiplier: '1.0x',
        description: '日常阅读、整理笔记、轻复盘'
      }
))

const activeTimelineTask = computed(() => (
  masterTimelineStore.masterTimeline.find((task) => task.id === masterTimelineStore.activeTaskId) || null
))

const placementType = computed(() => {
  const item = placementItem.value
  if (!item) return ''
  if (item.placementType) return item.placementType
  if (item.placement_type) return item.placement_type
  if (item.category === 'structures') return 'building'
  if (['plants', 'trees'].includes(item.category)) return 'greenery'
  return ''
})

const occupiedSlotIds = computed(() => {
  const occupied = new Set()
  placedDecorations.value.forEach((item) => {
    if (item.slot_id) occupied.add(item.slot_id)
  })
  return occupied
})

const compatibleSlots = computed(() => {
  const type = placementType.value
  if (!type) return []
  return citySlots.value.filter((slot) => (
    slot.enabled !== false &&
    slot.slot_type === type &&
    !occupiedSlotIds.value.has(slot.slot_id)
  ))
})

const slotFootprintById = computed(() => (
  Object.fromEntries(citySlots.value.map((slot) => [slot.slot_id, Number(slot.footprint || 0)]))
))

const previewSlot = computed(() => {
  if (!isPlacementMode.value) return null
  return compatibleSlots.value.find((slot) => slot.slot_id === hoveredPlacementSlotId.value) || compatibleSlots.value[0] || null
})

const previewTargetFootprint = computed(() => {
  if (!previewSlot.value) return 0
  return previewSlot.value.slot_type === 'building'
    ? Number(previewSlot.value.footprint || 2.2) * 0.82
    : Number(previewSlot.value.footprint || 1.8)
})

const loadCitySlots = async () => {
  try {
    const response = await axios.get(`${API_BASE}/static/city_layout_slots.json`)
    citySlots.value = response.data?.slots || []
  } catch (error) {
    console.error('Failed to load city slots', error)
    citySlots.value = []
  }
}

const upsertPlacedDecoration = (item) => {
  if (!item?.id) return
  const next = placedDecorations.value.filter((entry) => entry.id !== item.id)
  next.push(item)
  next.sort((left, right) => (left.id || 0) - (right.id || 0))
  placedDecorations.value = next
}

const loadPlacedDecorations = async ({ preserveExisting = false, fallbackItem = null, showRefreshError = false } = {}) => {
  try {
    const response = await unifiedShopApi.placed(currentUsername.value, { dimension: '3D' })
    placedDecorations.value = response.data.items || []
    inventoryStore.replacePlacedItemsForDimension('PHYSICAL', response.data.items || [])
    return true
  } catch (error) {
    console.error('Failed to load placed physical assets', error)
    if (!preserveExisting) {
      placedDecorations.value = []
    }
    if (fallbackItem) {
      upsertPlacedDecoration(fallbackItem)
    }
    if (showRefreshError) {
      window.alert(error.response?.data?.detail || '部署已经成功，但刷新城市列表失败，请稍后手动刷新页面确认。')
    }
    return false
  }
}

const loadUserGrowth = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/growth/${currentUsername.value}`)
    userGrowth.value = {
      ...userGrowth.value,
      ...(response.data?.growth || response.data || {})
    }
  } catch (error) {
    console.error('Failed to load growth data', error)
  }
}

const changeDuration = (minutes) => {
  focusHubStore.setFocusMinutes(minutes)
}

const changeDifficulty = (value) => {
  focusHubStore.setTaskDifficulty(value)
}

const pushTerminalFeed = ({ status = 'resolved', content = '', severity = 'success', channel = 'system' }) => {
  terminalFeed.value = {
    id: Date.now() + Math.random(),
    status,
    content,
    severity,
    channel
  }
}

const clearRewardTimer = () => {
  if (focusRewardTimer) {
    window.clearTimeout(focusRewardTimer)
    focusRewardTimer = null
  }
}

const scheduleRewardReveal = (feedback = '') => {
  clearRewardTimer()
  const contentLength = String(feedback || '').trim().length
  const delay = Math.min(5200, Math.max(1100, contentLength * 42))
  focusRewardTimer = window.setTimeout(() => {
    showFocusRewardModal.value = true
  }, delay)
}

const startFocusSettlement = () => {
  pendingFocusDuration.value = focusHubStore.pomodoro.focusMinutes
  focusSessionLog.value = ''
  focusSettlementResult.value = null
  showFocusRewardModal.value = false
  showFocusDebrief.value = true
}

const closeFocusRewardModal = () => {
  showFocusRewardModal.value = false
}

const submitFocusComplete = async () => {
  if (isFocusSettlementSubmitting.value) return
  const duration = pendingFocusDuration.value || focusHubStore.pomodoro.focusMinutes
  isFocusSettlementSubmitting.value = true
  showAiWindow.value = true
  pushTerminalFeed({
    status: 'pending',
    content: '[量子算力评估中...]',
    severity: 'info',
    channel: 'system'
  })
  try {
    const data = await focusHubStore.completeFocusSession({
      username: currentUsername.value,
      duration,
      subject: '物理实体舱番茄钟',
      sessionLog: focusSessionLog.value,
      taskDifficulty: focusHubStore.pomodoro.taskDifficulty
    })
    focusSettlementResult.value = {
      ...(data || {}),
      duration,
      taskDifficulty: focusHubStore.pomodoro.taskDifficulty,
      sessionLog: focusSessionLog.value.trim()
    }
    showFocusDebrief.value = false
    pushTerminalFeed({
      status: 'resolved',
      content: data?.feedback || '评估完成，本轮收益已结算。',
      severity: data?.evaluation_source === 'fallback' ? 'warning' : 'success',
      channel: 'system'
    })
    await loadUserGrowth()
    focusHubStore.resolveFocusCompletion()
    scheduleRewardReveal(data?.feedback || '')
  } catch (error) {
    console.error('Failed to sync focus completion', error)
    pushTerminalFeed({
      status: 'resolved',
      content: '评估链路中断，本轮奖励未能同步，请稍后重试。',
      severity: 'warning',
      channel: 'system'
    })
    window.alert(error.response?.data?.detail || '专注结算失败，请稍后再试。')
  } finally {
    isFocusSettlementSubmitting.value = false
  }
}

const startFocus = () => {
  if (focusHubStore.pomodoro.isRunning || showFocusDebrief.value || isFocusSettlementSubmitting.value) return
  if (!focusHubStore.pomodoro.linkedTaskId && activeTimelineTask.value) {
    focusHubStore.linkTimelineTask(activeTimelineTask.value)
  }
  focusHubStore.startPomodoro()
}

const startTimelineTask = (task) => {
  if (!task) return
  focusHubStore.linkTimelineTask(task)
  masterTimelineStore.deployTask(task.id)
  showAiWindow.value = false
  focusHubStore.startPomodoro()
}

const handleNavSelection = (id) => {
  if (id === 'adjutant') {
    showAiWindow.value = true
    return
  }
  if (id === 'exchange') {
    router.push('/shop')
    return
  }
  if (id === 'fleet') {
    router.push('/collab')
    return
  }
  if (id === 'protocol') {
    router.push('/exam')
  }
}

const animateDraftDeployment = async ({ sourceRects = [] } = {}) => {
  if (props.previewMode || !sourceRects.length) return
  await nextTick()
  const target = document.querySelector('[data-master-timeline-dropzone]')?.getBoundingClientRect?.()
  if (!target) return

  sourceRects.slice(0, 5).forEach((entry, index) => {
    if (!entry?.rect) return
    const chip = document.createElement('div')
    chip.className = 'timeline-transfer-chip'
    chip.textContent = 'TASK'
    chip.style.left = `${entry.rect.left}px`
    chip.style.top = `${entry.rect.top}px`
    chip.style.width = `${Math.max(72, entry.rect.width)}px`
    chip.style.height = `${Math.max(36, entry.rect.height)}px`
    document.body.appendChild(chip)

    requestAnimationFrame(() => {
      const deltaX = target.left + Math.min(40, target.width * 0.2) - entry.rect.left + index * 8
      const deltaY = target.top + 26 + index * 10 - entry.rect.top
      chip.style.transform = `translate(${deltaX}px, ${deltaY}px) scale(0.62)`
      chip.style.opacity = '0.12'
    })

    window.setTimeout(() => chip.remove(), 700)
  })
}

const setPreviewSlot = (slot) => {
  if (!slot?.slot_id) return
  hoveredPlacementSlotId.value = slot.slot_id
}

const getSafeCityY = (value) => Math.max(Number(value ?? SAFE_CITY_Y), SAFE_CITY_Y) + 0.01

const resetPreviewSlot = () => {
  hoveredPlacementSlotId.value = compatibleSlots.value[0]?.slot_id || ''
}

const getSlotMarkerRadius = (slot) => Number(slot?.footprint || (slot?.slot_type === 'building' ? 2.2 : 1.8)) * 0.86

const getSlotRingArgs = (slot) => {
  const footprint = Number(slot?.footprint || (slot?.slot_type === 'building' ? 2.2 : 1.8))
  if (slot?.slot_type === 'building') {
    return [footprint * 0.35, footprint * 0.63, 6]
  }
  return [footprint * 0.31, footprint * 0.57, 24]
}

const handleSlotPointerEnter = (slot) => {
  if (!isPlacementMode.value) return
  setPreviewSlot(slot)
}

const syncPlacementModeFromStore = () => {
  if (props.previewMode) return
  const draft = inventoryStore.placementDraft
  if (dimensionStore.activeDimension !== 'PHYSICAL' || !draft || draft.dimension !== 'PHYSICAL') {
    if (!isPlacementSubmitting.value) {
      isPlacementMode.value = false
      placementItem.value = null
      hoveredPlacementSlotId.value = ''
    }
    return
  }

  placementItem.value = draft
  selectedDecoration.value = null
  isPlacementMode.value = true

  if (!citySlots.value.length) {
    return
  }

  if (!['building', 'greenery'].includes(placementType.value)) {
    window.alert('这个 3D 物品当前不支持在城市中放置。')
    inventoryStore.cancelPlacement()
    return
  }

  if (!compatibleSlots.value.length) {
    const message = placementType.value === 'greenery' ? '当前没有空闲绿化位' : '当前没有空闲建筑位'
    window.alert(message)
    inventoryStore.cancelPlacement()
    return
  }

  if (!compatibleSlots.value.some((slot) => slot.slot_id === hoveredPlacementSlotId.value)) {
    resetPreviewSlot()
  }
}

const handleSlotClick = async (slot) => {
  if (!slot) return
  if (!supportsHover.value && previewSlot.value?.slot_id !== slot.slot_id) {
    setPreviewSlot(slot)
    return
  }
  await confirmPlacement(slot)
}

const exitPlacementMode = () => {
  if (isPlacementSubmitting.value) return
  isPlacementMode.value = false
  placementItem.value = null
  hoveredPlacementSlotId.value = ''
  inventoryStore.cancelPlacement()
}

const confirmPlacement = async (slot) => {
  if (isPlacementSubmitting.value || !placementItem.value || !slot?.slot_id) return
  isPlacementSubmitting.value = true
  try {
    const response = await unifiedShopApi.place(
      currentUsername.value,
      placementItem.value.itemId || placementItem.value.item_id || placementItem.value.id,
      slot.slot_id,
      slot.x || 0,
      getSafeCityY(slot.y),
      slot.z || 0,
      slot.rotation_y || 0,
      1.0,
      'city',
      '3D'
    )
    const placedItem = response.data?.placed_item || null
    if (placedItem) {
      selectedDecoration.value = placedItem
      upsertPlacedDecoration(placedItem)
      inventoryStore.completePlacement(placedItem, placementItem.value)
    }
    isPlacementMode.value = false
    placementItem.value = null
    hoveredPlacementSlotId.value = ''
    await loadPlacedDecorations({
      preserveExisting: true,
      fallbackItem: placedItem,
      showRefreshError: Boolean(placedItem)
    })
  } catch (error) {
    window.alert(error.response?.data?.detail || '放置失败，请稍后再试。')
  } finally {
    isPlacementSubmitting.value = false
  }
}

const deleteSelectedDecoration = async () => {
  if (!selectedDecoration.value) return
  const target = selectedDecoration.value
  if (!window.confirm(`确认移除 ${target.name_cn || target.name} 吗？`)) return
  try {
    await unifiedShopApi.removePlaced(target.id, currentUsername.value)
    inventoryStore.handlePlacedItemRemoval(target)
    await inventoryStore.refreshInventory(currentUsername.value)
    selectedDecoration.value = null
    await loadPlacedDecorations()
  } catch (error) {
    window.alert(error.response?.data?.detail || '移除失败。')
  }
}

const selectDecoration = (item) => {
  if (isPlacementMode.value) return
  selectedDecoration.value = selectedDecoration.value?.id === item.id ? null : item
}

const consumePendingPlacement = () => {
  inventoryStore.consumeLegacyPendingPlacement()
}

watch(compatibleSlots, (slots) => {
  if (!isPlacementMode.value) return
  if (!slots.length) {
    hoveredPlacementSlotId.value = ''
    return
  }
  if (!slots.some((slot) => slot.slot_id === hoveredPlacementSlotId.value)) {
    hoveredPlacementSlotId.value = slots[0].slot_id
  }
})

watch(
  () => [inventoryStore.placementDraft, inventoryStore.placementMode, dimensionStore.activeDimension, citySlots.value.length],
  () => {
    syncPlacementModeFromStore()
  },
  { immediate: true }
)

watch(previewSlot, (slot) => {
  if (!slot || !placementItem.value || props.previewMode) return
  inventoryStore.updateGhostPreview({
    slotId: slot.slot_id,
    x: slot.x,
    y: getSafeCityY(slot.y),
    z: slot.z,
    rotationY: slot.rotation_y || 0
  })
})

const handleKeydown = (event) => {
  if (event.key === 'Escape' && isPlacementMode.value) {
    exitPlacementMode()
  }
  if (event.key === 'Delete' && selectedDecoration.value) {
    deleteSelectedDecoration()
  }
}

watch(() => focusHubStore.pomodoro.pendingSettlement, (pending) => {
  if (pending && focusHubStore.pomodoro.mode === 'focus') {
    startFocusSettlement()
  }
})

onMounted(async () => {
  supportsHover.value = window.matchMedia('(hover: hover) and (pointer: fine)').matches
  masterTimelineStore.hydrateToday(currentUsername.value)
  focusHubStore.hydrate(currentUsername.value)
  const bootstrapTasks = props.previewMode
    ? [loadCitySlots(), loadPlacedDecorations()]
    : [loadCitySlots(), loadPlacedDecorations(), loadUserGrowth()]
  await Promise.all(bootstrapTasks)
  if (!props.previewMode) {
    consumePendingPlacement()
    window.addEventListener('keydown', handleKeydown)
  }
})

onUnmounted(() => {
  clearRewardTimer()
  if (!props.previewMode) {
    window.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<template>
  <div class="city-scene-page" :class="{ 'preview-mode': props.previewMode }">
    <div v-if="isPlacementMode && !props.previewMode" class="placement-banner kenney-hud-panel">
      <div class="placement-copy">
        <span class="placement-badge">{{ placementType === 'building' ? '建筑槽位' : '绿化槽位' }}</span>
        <strong>正在放置 {{ placementItem?.nameCn || placementItem?.name || placementItem?.name_cn || placementItem?.name }}</strong>
        <span>{{ isPlacementSubmitting ? '正在完成部署...' : '点击发光槽位即可完成部署' }}</span>
      </div>
      <button class="banner-btn kenney-hud-btn kenney-hud-btn--small kenney-hud-btn--danger" type="button" :disabled="isPlacementSubmitting" @click="exitPlacementMode">
        取消
      </button>
    </div>

    <div class="skyline-overlay">
      <div class="horizon"></div>
      <div class="orbital-ring orbital-ring-a"></div>
      <div class="orbital-ring orbital-ring-b"></div>
      <div class="city-haze"></div>
    </div>

    <div class="canvas-layer">
      <TresCanvas :clear-color="CITY_THEME.sky" :window-size="!props.previewMode">
        <TresPerspectiveCamera :position="[22, 16, 20]" :look-at="[0, 2.2, 0]" />
        <OrbitControls
          :enable-damping="true"
          :damping-factor="0.06"
          :min-distance="10"
          :max-distance="30"
          :max-polar-angle="Math.PI / 2.08"
        />

        <TresAmbientLight :color="CITY_THEME.ambient" :intensity="CITY_THEME.ambientIntensity" />
        <TresDirectionalLight :position="[10, 18, 8]" :color="CITY_THEME.directional" :intensity="CITY_THEME.directionalIntensity" />
        <TresDirectionalLight :position="[-10, 12, -6]" color="#6d5cff" :intensity="0.6" />

        <TresMesh :position="[0, -1.55, 0]" :rotation="[-Math.PI / 2, 0, 0]">
          <TresPlaneGeometry :args="[120, 120]" />
          <TresMeshStandardMaterial :color="CITY_THEME.fogPlane" />
        </TresMesh>

        <TresMesh :position="[0, -1.5, -16]">
          <TresBoxGeometry :args="[42, 10, 0.3]" />
          <TresMeshStandardMaterial color="#13203a" :emissive="CITY_THEME.horizonGlow" :emissive-intensity="0.18" :transparent="true" :opacity="0.35" />
        </TresMesh>

        <FloatingIsland :scale="1" theme="city" />

        <TresGroup
          v-if="isPlacementMode && placementItem && previewSlot"
          :position="[previewSlot.x, getSafeCityY(previewSlot.y), previewSlot.z]"
          :rotation="[0, ((previewSlot.rotation_y || 0) * Math.PI) / 180, 0]"
        >
          <CityModelInstance
            :item="placementItem"
            :ghost="true"
            :target-footprint="previewTargetFootprint"
          />
        </TresGroup>

        <TresGroup
          v-for="slot in compatibleSlots"
          :key="slot.slot_id"
          :position="[slot.x, getSafeCityY(slot.y) + 0.11, slot.z]"
        >
          <TresMesh
            :position="[0, 0.02, 0]"
            :rotation="[-Math.PI / 2, 0, 0]"
            :render-order="12"
            @pointerenter.stop="handleSlotPointerEnter(slot)"
            @pointermove.stop="handleSlotPointerEnter(slot)"
            @click.stop="handleSlotClick(slot)"
          >
            <TresCircleGeometry :args="[getSlotMarkerRadius(slot), 32]" />
            <TresMeshBasicMaterial
              :color="slot.slot_type === 'building' ? '#73e0ff' : '#53f0b0'"
              :transparent="true"
              :opacity="0.1"
              :depth-test="false"
              :depth-write="false"
            />
          </TresMesh>
          <TresMesh
            :position="[0, 0.48, 0]"
            :render-order="11"
            @pointerenter.stop="handleSlotPointerEnter(slot)"
            @pointermove.stop="handleSlotPointerEnter(slot)"
            @click.stop="handleSlotClick(slot)"
          >
            <TresCylinderGeometry :args="[slot.slot_type === 'building' ? 0.34 : 0.28, slot.slot_type === 'building' ? 0.18 : 0.14, 0.92, 24, 1, true]" />
            <TresMeshBasicMaterial
              :color="slot.slot_type === 'building' ? '#73e0ff' : '#53f0b0'"
              :transparent="true"
              :opacity="0.16"
              :depth-test="false"
              :depth-write="false"
            />
          </TresMesh>
          <TresMesh
            :position="[0, 0.05, 0]"
            :rotation="[-Math.PI / 2, 0, 0]"
            :render-order="13"
            @pointerenter.stop="handleSlotPointerEnter(slot)"
            @pointermove.stop="handleSlotPointerEnter(slot)"
            @click.stop="handleSlotClick(slot)"
          >
            <TresRingGeometry :args="getSlotRingArgs(slot)" />
            <TresMeshBasicMaterial
              :color="slot.slot_type === 'building' ? '#73e0ff' : '#53f0b0'"
              :transparent="true"
              :opacity="slot.slot_type === 'building' ? 0.82 : 0.78"
              :depth-test="false"
              :depth-write="false"
            />
          </TresMesh>
          <TresMesh
            :position="[0, 0.12, 0]"
            :render-order="14"
            @pointerenter.stop="handleSlotPointerEnter(slot)"
            @pointermove.stop="handleSlotPointerEnter(slot)"
            @click.stop="handleSlotClick(slot)"
          >
            <TresCylinderGeometry :args="[0.1, 0.1, 0.22, 12]" />
            <TresMeshBasicMaterial
              :color="slot.slot_type === 'building' ? '#73e0ff' : '#53f0b0'"
              :transparent="true"
              :opacity="0.95"
              :depth-test="false"
              :depth-write="false"
            />
          </TresMesh>
        </TresGroup>

        <PlacedModel
          v-for="deco in placedDecorations"
          :key="deco.id"
          :item="deco"
          :is-selected="selectedDecoration?.id === deco.id"
          :slot-footprint="slotFootprintById[deco.slot_id] || 0"
          @select="selectDecoration(deco)"
        />
      </TresCanvas>
    </div>

    <TopStatusBar
      v-if="!props.previewMode"
      :focus-energy="userGrowth.focus_energy || 0"
      :focus-minutes="focusMinutes"
      :streak-days="userGrowth.streak_days || 0"
    />

    <LeftSidebar
      v-if="!props.previewMode"
      :formatted-time="formattedTime"
      :is-running="focusHubStore.pomodoro.isRunning"
      :focus-progress="focusProgress"
      :duration-options="durationOptions"
      :selected-duration="focusHubStore.pomodoro.focusMinutes"
      :selected-difficulty="focusHubStore.pomodoro.taskDifficulty"
      :focus-energy="userGrowth.focus_energy || 0"
      :user-growth="userGrowth"
      :mode="focusHubStore.pomodoro.mode"
      :completed-sessions="focusHubStore.pomodoro.completedFocusSessions"
      @start-focus="startFocus"
      @change-duration="changeDuration"
      @change-difficulty="changeDifficulty"
    />

    <RightSidebar
      v-if="!props.previewMode"
      @draft-deployed="animateDraftDeployment"
      @start-timeline-task="startTimelineTask"
    />

    <TopActionBar v-if="!props.previewMode" />

    <div v-if="!props.previewMode" class="dock-stack">
      <DockWindow v-if="showAiWindow" title="副官终端" icon="AI" accent="gold" @close="showAiWindow = false">
        <AIAssistantDock :username="currentUsername" :system-feed="terminalFeed" />
      </DockWindow>
    </div>

    <div v-if="showFocusDebrief && !props.previewMode" class="focus-modal-backdrop">
      <div class="focus-modal kenney-hud-panel">
        <span class="focus-modal-kicker">Focus Debrief</span>
        <h3>专注结束，提交一句算力日志</h3>
        <p class="focus-modal-copy">
          本轮时长 {{ pendingFocusDuration || focusHubStore.pomodoro.focusMinutes }} 分钟，当前脑力负载为
          <strong>{{ selectedDifficultyMeta.label }}</strong>
          <span class="focus-modal-multiplier">收益基准 {{ selectedDifficultyMeta.multiplier }}</span>
        </p>
        <textarea
          v-model="focusSessionLog"
          class="focus-log-input"
          placeholder="例如：今天把高数极限题的换元思路重新梳理了一遍，第三题终于能独立推出来。"
          :disabled="isFocusSettlementSubmitting"
        />
        <div class="focus-difficulty-summary">
          <strong>{{ selectedDifficultyMeta.label }}</strong>
          <span>{{ selectedDifficultyMeta.description }}</span>
        </div>
        <div class="focus-modal-actions">
          <button
            type="button"
            class="selected-btn"
            :disabled="isFocusSettlementSubmitting"
            @click="submitFocusComplete"
          >
            {{ isFocusSettlementSubmitting ? '评估中...' : '提交评估' }}
          </button>
          <button
            type="button"
            class="selected-btn danger"
            :disabled="isFocusSettlementSubmitting"
            @click="focusSessionLog = ''; submitFocusComplete()"
          >
            空日志减半结算
          </button>
        </div>
      </div>
    </div>

    <div v-if="showFocusRewardModal && focusSettlementResult && !props.previewMode" class="focus-modal-backdrop reward-backdrop">
      <div class="focus-modal reward-modal kenney-hud-panel">
        <span class="focus-modal-kicker">Quantum Settlement</span>
        <h3>本轮结算完成</h3>
        <div class="reward-energy">{{ focusSettlementResult.final_energy || 0 }}</div>
        <p class="focus-modal-copy">专注能量已入账，终端反馈已经同步到舰桥副官。</p>
        <div class="reward-grid">
          <div class="reward-chip">
            <span>时长</span>
            <strong>{{ focusSettlementResult.duration }}m</strong>
          </div>
          <div class="reward-chip">
            <span>难度倍率</span>
            <strong>{{ focusSettlementResult.task_difficulty_multiplier || '1.0' }}x</strong>
          </div>
          <div class="reward-chip">
            <span>质量倍率</span>
            <strong>{{ focusSettlementResult.quality_multiplier || '1.0' }}x</strong>
          </div>
        </div>
        <button type="button" class="selected-btn" @click="closeFocusRewardModal">继续舰桥任务</button>
      </div>
    </div>

    <div v-if="selectedDecoration && !isPlacementMode && !props.previewMode" class="selected-bar kenney-hud-panel">
      <span class="selected-name">{{ selectedDecoration.name_cn || selectedDecoration.name }}</span>
      <span class="selected-slot">{{ selectedDecoration.slot_id || '已部署实体' }}</span>
      <button type="button" class="selected-btn danger" @click="deleteSelectedDecoration">移除</button>
      <button type="button" class="selected-btn" @click="selectedDecoration = null">关闭</button>
    </div>

    <MobileNav v-if="!props.previewMode" />
  </div>
</template>

<style scoped>
.city-scene-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 18%, rgba(109, 92, 255, 0.25), transparent 24%),
    radial-gradient(circle at 50% 34%, rgba(76, 222, 255, 0.18), transparent 30%),
    linear-gradient(180deg, #02050e 0%, #050914 42%, #0a1122 72%, #08101e 100%);
  color: #eef7ff;
}

.city-scene-page.preview-mode {
  width: 100%;
  height: 100%;
  border-radius: 18px;
  background:
    radial-gradient(circle at 50% 18%, rgba(109, 92, 255, 0.18), transparent 28%),
    radial-gradient(circle at 50% 34%, rgba(76, 222, 255, 0.14), transparent 30%),
    linear-gradient(180deg, #040814 0%, #08111f 48%, #0a192f 100%);
}

.canvas-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.skyline-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.horizon {
  position: absolute;
  left: 50%;
  bottom: 20%;
  width: min(80vw, 920px);
  height: 240px;
  transform: translateX(-50%);
  background:
    linear-gradient(180deg, rgba(79, 115, 255, 0.02), rgba(79, 115, 255, 0.14)),
    repeating-linear-gradient(
      90deg,
      rgba(125, 177, 255, 0.12) 0,
      rgba(125, 177, 255, 0.12) 14px,
      transparent 14px,
      transparent 34px
    );
  clip-path: polygon(0 100%, 2% 64%, 6% 64%, 6% 42%, 11% 42%, 11% 78%, 16% 78%, 16% 30%, 22% 30%, 22% 70%, 29% 70%, 29% 24%, 36% 24%, 36% 84%, 41% 84%, 41% 44%, 48% 44%, 48% 18%, 54% 18%, 54% 74%, 62% 74%, 62% 36%, 69% 36%, 69% 62%, 76% 62%, 76% 26%, 83% 26%, 83% 72%, 90% 72%, 90% 54%, 95% 54%, 95% 100%);
  filter: drop-shadow(0 0 36px rgba(109, 92, 255, 0.3));
}

.orbital-ring {
  position: absolute;
  border-radius: 999px;
  border: 1px solid rgba(115, 224, 255, 0.16);
}

.orbital-ring-a {
  width: 620px;
  height: 620px;
  top: -230px;
  left: 50%;
  transform: translateX(-50%);
}

.orbital-ring-b {
  width: 760px;
  height: 760px;
  top: -300px;
  left: 50%;
  transform: translateX(-50%) rotate(18deg);
  border-color: rgba(109, 92, 255, 0.16);
}

.city-haze {
  position: absolute;
  left: 50%;
  bottom: 16%;
  width: min(90vw, 1040px);
  height: 220px;
  transform: translateX(-50%);
  background: radial-gradient(circle, rgba(76, 222, 255, 0.16), transparent 64%);
  filter: blur(26px);
}

.placement-banner {
  position: fixed;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 12;
  width: min(640px, calc(100vw - 24px));
  padding: 12px 16px;
  border-radius: 20px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.placement-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.placement-badge {
  display: inline-flex;
  width: fit-content;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(76, 222, 255, 0.12);
  font-size: 11px;
  font-weight: 700;
}

.banner-btn {
  min-width: 84px;
}

.dock-stack {
  position: absolute;
  right: 146px;
  bottom: 22px;
  z-index: 11;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-end;
}

.selected-bar {
  position: fixed;
  left: 50%;
  bottom: 82px;
  transform: translateX(-50%);
  z-index: 10;
  min-width: 280px;
  max-width: calc(100vw - 24px);
  border-radius: 20px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.selected-name {
  font-weight: 800;
}

.selected-slot {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.72);
}

.selected-btn {
  margin-left: auto;
  border: none;
  border-radius: 12px;
  padding: 9px 14px;
  background: rgba(255, 255, 255, 0.08);
  color: #eef7ff;
  cursor: pointer;
}

.selected-btn.danger {
  margin-left: 0;
  background: rgba(255, 101, 133, 0.16);
}

.focus-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(2, 6, 18, 0.72);
  backdrop-filter: blur(14px);
}

.focus-modal {
  width: min(560px, calc(100vw - 24px));
  border-radius: 24px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.focus-modal-kicker {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(115, 224, 255, 0.78);
}

.focus-modal h3 {
  margin: 0;
  font-size: 28px;
}

.focus-modal-copy {
  margin: 0;
  color: rgba(222, 240, 255, 0.76);
  line-height: 1.6;
}

.focus-modal-multiplier {
  display: inline-block;
  margin-left: 8px;
  color: #7ff4ff;
}

.focus-log-input {
  min-height: 148px;
  border: 1px solid rgba(115, 224, 255, 0.2);
  border-radius: 18px;
  background: rgba(7, 14, 32, 0.82);
  color: #eef7ff;
  padding: 14px 16px;
  resize: vertical;
  outline: none;
  font: inherit;
  line-height: 1.6;
}

.focus-difficulty-summary {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  border-radius: 16px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(222, 240, 255, 0.78);
}

.focus-modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.focus-modal .selected-btn {
  margin-left: 0;
}

.reward-backdrop {
  background: rgba(1, 10, 26, 0.8);
}

.reward-modal {
  align-items: center;
  text-align: center;
}

.reward-energy {
  font-size: 64px;
  line-height: 1;
  font-weight: 900;
  color: #7ef4ff;
  text-shadow: 0 0 28px rgba(115, 224, 255, 0.22);
}

.reward-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.reward-chip {
  border-radius: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reward-chip span {
  font-size: 12px;
  color: rgba(222, 240, 255, 0.68);
}

:global(.timeline-transfer-chip) {
  position: fixed;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(0, 255, 255, 0.36);
  background: rgba(7, 16, 34, 0.94);
  color: #eefdff;
  font-family: 'Roboto Mono', 'Consolas', monospace;
  font-size: 11px;
  letter-spacing: 0.12em;
  pointer-events: none;
  box-shadow: 0 0 22px rgba(0, 255, 255, 0.18);
  transition: transform 0.68s cubic-bezier(0.2, 0.75, 0.15, 1), opacity 0.68s ease;
}

@media (max-width: 768px) {
  .dock-stack {
    left: 12px;
    right: 12px;
    bottom: 166px;
    align-items: stretch;
  }

  .selected-bar {
    bottom: 158px;
    padding: 12px;
    flex-wrap: wrap;
  }

  .focus-modal {
    padding: 18px;
  }

  .focus-modal h3 {
    font-size: 24px;
  }

  .focus-difficulty-summary,
  .focus-modal-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .reward-grid {
    grid-template-columns: 1fr;
  }
}
</style>
