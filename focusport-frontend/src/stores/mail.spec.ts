/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useMailStore } from './mail'
import { messageApi } from '../api'

vi.mock('../api', () => ({
  messageApi: {
    unread: vi.fn(),
    list: vi.fn(),
    markRead: vi.fn()
  }
}))

const flushAsync = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

describe('mail store', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts polling once and stops cleanly', async () => {
    vi.mocked(messageApi.unread).mockResolvedValue({ data: { unread: 3 } } as never)

    const store = useMailStore()
    await store.startPolling('alice')
    expect(store.polling).toBe(true)
    expect(store.unreadCount).toBe(3)
    expect(messageApi.unread).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(30000)
    await flushAsync()
    expect(messageApi.unread).toHaveBeenCalledTimes(2)

    store.stopPolling()
    expect(store.polling).toBe(false)

    vi.advanceTimersByTime(30000)
    await flushAsync()
    expect(messageApi.unread).toHaveBeenCalledTimes(2)
  })

  it('marks message as read and never decrements below zero', async () => {
    vi.mocked(messageApi.list).mockResolvedValue({
      data: {
        messages: [
          { id: 11, is_read: false, title: 'hello', content: 'world', category: 'system' }
        ]
      }
    } as never)
    vi.mocked(messageApi.markRead).mockResolvedValue({ data: { ok: true } } as never)

    const store = useMailStore()
    store.unreadCount = 1

    await store.loadPreview('alice')
    const first = await store.markRead(11)
    const second = await store.markRead(11)

    expect(first).toBe(true)
    expect(second).toBe(true)
    expect(store.unreadCount).toBe(0)
    expect(store.previewMessages[0].is_read).toBe(true)
    expect(messageApi.markRead).toHaveBeenCalledTimes(1)
  })
})
