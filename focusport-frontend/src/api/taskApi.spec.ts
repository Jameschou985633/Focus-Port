import { describe, expect, it, vi } from 'vitest'

const axiosMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  put: vi.fn(),
  interceptors: {
    request: { use: vi.fn() },
    response: { use: vi.fn() }
  }
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => axiosMock)
  }
}))

describe('taskApi', () => {
  it('maps FocusHub task metadata to the Todo backend contract', async () => {
    const { taskApi } = await import('./index')

    await taskApi.add('alice', 'Review design', {
      scheduledDate: '2026-04-20',
      scheduledTime: '10:00',
      status: 'todo',
      category: 'Design',
      accent: '#4880FF'
    })

    expect(axiosMock.post).toHaveBeenCalledWith('/api/todo/add', {
      username: 'alice',
      content: 'Review design',
      scheduled_date: '2026-04-20',
      scheduled_time: '10:00',
      status: 'todo',
      category: 'Design',
      accent: '#4880FF'
    })
  })
})
