import { defineStore } from 'pinia'
import { ref } from 'vue'
import { messageApi } from '../api'

const POLL_INTERVAL_MS = 30000

export const useMailStore = defineStore('mail', () => {
  const unreadCount = ref(0)
  const previewMessages = ref([])
  const isLoading = ref(false)
  const polling = ref(false)

  const activeUsername = ref('')
  let pollTimer = null

  const clearPollTimer = () => {
    if (pollTimer) {
      window.clearInterval(pollTimer)
      pollTimer = null
    }
  }

  const refreshUnread = async (username = activeUsername.value) => {
    const normalizedUsername = String(username || '').trim()
    if (!normalizedUsername) {
      unreadCount.value = 0
      return 0
    }

    try {
      const res = await messageApi.unread(normalizedUsername)
      unreadCount.value = Math.max(0, Number(res?.data?.unread || 0))
    } catch {
      unreadCount.value = 0
    }

    return unreadCount.value
  }

  const loadPreview = async (username = activeUsername.value) => {
    const normalizedUsername = String(username || '').trim()
    if (!normalizedUsername) {
      previewMessages.value = []
      return []
    }

    isLoading.value = true
    try {
      const res = await messageApi.list(normalizedUsername)
      previewMessages.value = (res?.data?.messages || []).slice(0, 15)
    } catch {
      previewMessages.value = []
    } finally {
      isLoading.value = false
    }

    return previewMessages.value
  }

  const markRead = async (msgId) => {
    const id = Number(msgId)
    if (!Number.isFinite(id)) return false

    const target = previewMessages.value.find((msg) => Number(msg.id) === id)
    if (target?.is_read) return true

    try {
      await messageApi.markRead(id)
      if (target) target.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
      return true
    } catch {
      return false
    }
  }

  const stopPolling = () => {
    clearPollTimer()
    polling.value = false
    activeUsername.value = ''
  }

  const startPolling = async (username) => {
    const normalizedUsername = String(username || '').trim()
    if (!normalizedUsername) {
      stopPolling()
      unreadCount.value = 0
      previewMessages.value = []
      return
    }

    activeUsername.value = normalizedUsername
    polling.value = true

    await refreshUnread(normalizedUsername)

    clearPollTimer()
    pollTimer = window.setInterval(() => {
      refreshUnread(activeUsername.value)
    }, POLL_INTERVAL_MS)
  }

  return {
    unreadCount,
    previewMessages,
    isLoading,
    polling,
    startPolling,
    stopPolling,
    refreshUnread,
    loadPreview,
    markRead
  }
})
