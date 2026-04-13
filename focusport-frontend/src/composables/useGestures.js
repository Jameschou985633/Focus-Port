/**
 * Touch Gesture Composables
 * 触控手势组合式函数
 */

import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 滑动手势检测
 * @param {Object} options - 配置选项
 * @param {number} options.threshold - 滑动阈值（像素）
 * @param {number} options.timeout - 滑动超时时间（毫秒）
 * @returns {Object} - { direction, deltaX, deltaY, isSwiping }
 */
export function useSwipe(options = {}) {
  const {
    threshold = 50,
    timeout = 300,
    onSwipeLeft,
    onSwipeRight,
    onSwipeUp,
    onSwipeDown
  } = options

  const touchStart = ref({ x: 0, y: 0, time: 0 })
  const touchEnd = ref({ x: 0, y: 0 })
  const isSwiping = ref(false)
  const direction = ref(null)
  const deltaX = ref(0)
  const deltaY = ref(0)

  const onTouchStart = (e) => {
    const touch = e.touches[0]
    touchStart.value = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now()
    }
    isSwiping.value = true
    direction.value = null
  }

  const onTouchMove = (e) => {
    if (!isSwiping.value) return
    const touch = e.touches[0]
    touchEnd.value = { x: touch.clientX, y: touch.clientY }
    deltaX.value = touchEnd.value.x - touchStart.value.x
    deltaY.value = touchEnd.value.y - touchStart.value.y
  }

  const onTouchEnd = () => {
    if (!isSwiping.value) return
    isSwiping.value = false

    const elapsed = Date.now() - touchStart.value.time
    if (elapsed > timeout) return

    const absX = Math.abs(deltaX.value)
    const absY = Math.abs(deltaY.value)

    if (absX > threshold || absY > threshold) {
      if (absX > absY) {
        // 水平滑动
        direction.value = deltaX.value > 0 ? 'right' : 'left'
        if (direction.value === 'left' && onSwipeLeft) onSwipeLeft()
        if (direction.value === 'right' && onSwipeRight) onSwipeRight()
      } else {
        // 垂直滑动
        direction.value = deltaY.value > 0 ? 'down' : 'up'
        if (direction.value === 'up' && onSwipeUp) onSwipeUp()
        if (direction.value === 'down' && onSwipeDown) onSwipeDown()
      }
    }
  }

  return {
    direction,
    deltaX,
    deltaY,
    isSwiping,
    onTouchStart,
    onTouchMove,
    onTouchEnd
  }
}

/**
 * 双指缩放手势检测
 * @param {Object} options - 配置选项
 * @param {number} options.minScale - 最小缩放比例
 * @param {number} options.maxScale - 最大缩放比例
 * @returns {Object} - { scale, isPinching, onPinchStart, onPinchMove, onPinchEnd }
 */
export function usePinch(options = {}) {
  const { minScale = 0.5, maxScale = 3.0, onScaleChange } = options

  const scale = ref(1)
  const isPinching = ref(false)
  const startDistance = ref(0)
  const lastScale = ref(1)

  const getDistance = (touches) => {
    const dx = touches[0].clientX - touches[1].clientX
    const dy = touches[0].clientY - touches[1].clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  const onPinchStart = (e) => {
    if (e.touches.length !== 2) return
    isPinching.value = true
    startDistance.value = getDistance(e.touches)
  }

  const onPinchMove = (e) => {
    if (!isPinching.value || e.touches.length !== 2) return
    e.preventDefault()

    const currentDistance = getDistance(e.touches)
    const newScale = lastScale.value * (currentDistance / startDistance.value)

    // 限制缩放范围
    scale.value = Math.min(maxScale, Math.max(minScale, newScale))

    if (onScaleChange) {
      onScaleChange(scale.value)
    }
  }

  const onPinchEnd = () => {
    if (isPinching.value) {
      lastScale.value = scale.value
      isPinching.value = false
    }
  }

  return {
    scale,
    isPinching,
    onPinchStart,
    onPinchMove,
    onPinchEnd
  }
}

/**
 * 长按手势检测
 * @param {Object} options - 配置选项
 * @param {number} options.duration - 长按触发时间（毫秒）
 * @returns {Object} - { isLongPress, onStart, onEnd }
 */
export function useLongPress(options = {}) {
  const { duration = 500, onLongPress } = options

  const isLongPress = ref(false)
  let timer = null

  const onStart = () => {
    timer = setTimeout(() => {
      isLongPress.value = true
      if (onLongPress) {
        onLongPress()
        // 触觉反馈
        if (navigator.vibrate) {
          navigator.vibrate(50)
        }
      }
    }, duration)
  }

  const onEnd = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    isLongPress.value = false
  }

  return {
    isLongPress,
    onStart,
    onEnd
  }
}

/**
 * 触觉反馈
 * @param {number} duration - 震动持续时间（毫秒）
 */
export function useHapticFeedback() {
  const vibrate = (duration = 10) => {
    if (navigator.vibrate) {
      navigator.vibrate(duration)
    }
  }

  const vibrateLight = () => vibrate(10)
  const vibrateMedium = () => vibrate(25)
  const vibrateHeavy = () => vibrate(50)

  return {
    vibrate,
    vibrateLight,
    vibrateMedium,
    vibrateHeavy
  }
}

/**
 * 检测设备是否支持触控
 * @returns {boolean}
 */
export function useIsTouchDevice() {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0
}

/**
 * 滑动删除/操作手势
 * @param {Object} options - 配置选项
 * @returns {Object} - { translateX, isRevealed, onSwipeStart, onSwipeMove, onSwipeEnd, reset }
 */
export function useSwipeAction(options = {}) {
  const { threshold = 80, onReveal, onHide } = options

  const translateX = ref(0)
  const isRevealed = ref(false)
  const startX = ref(0)
  const isDragging = ref(false)

  const onSwipeStart = (e) => {
    isDragging.value = true
    startX.value = e.touches[0].clientX - translateX.value
  }

  const onSwipeMove = (e) => {
    if (!isDragging.value) return
    const currentX = e.touches[0].clientX
    const diff = currentX - startX.value

    // 限制滑动范围
    if (diff <= 0 && diff >= -threshold * 1.5) {
      translateX.value = diff
    }
  }

  const onSwipeEnd = () => {
    isDragging.value = false

    if (translateX.value <= -threshold) {
      // 显示操作按钮
      translateX.value = -threshold
      isRevealed.value = true
      if (onReveal) onReveal()
    } else {
      // 隐藏操作按钮
      translateX.value = 0
      isRevealed.value = false
      if (onHide) onHide()
    }
  }

  const reset = () => {
    translateX.value = 0
    isRevealed.value = false
  }

  return {
    translateX,
    isRevealed,
    onSwipeStart,
    onSwipeMove,
    onSwipeEnd,
    reset
  }
}
