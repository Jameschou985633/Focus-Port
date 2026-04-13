/* @vitest-environment jsdom */
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DaySummaryPanel from './DaySummaryPanel.vue'

const getDaySummary = vi.fn()
const getNextDaySeedTask = vi.fn()

vi.mock('../stores/useTaskStore', () => ({
  useTaskStore: () => ({
    getDaySummary,
    getNextDaySeedTask
  })
}))

describe('DaySummaryPanel', () => {
  beforeEach(() => {
    getDaySummary.mockReset()
    getNextDaySeedTask.mockReset()
    getDaySummary.mockReturnValue({
      dateKey: '2026-04-13',
      completedCount: 2,
      totalFocusSeconds: 5400,
      totalPomodoros: 3,
      totalComputePowerGained: 50,
      totalExpGained: 20,
      completedTasks: [
        { id: 'done-1', title: '完成任务 A' },
        { id: 'done-2', title: '完成任务 B' }
      ],
      pendingTasks: [
        { id: 'todo-1', title: '未完成任务', isCarriedOver: true, carryOverCount: 2 },
        { id: 'todo-2', title: '普通待办', isCarriedOver: false, carryOverCount: 0 }
      ]
    })
    getNextDaySeedTask.mockReturnValue({
      id: 'todo-1',
      title: '未完成任务',
      priority: 3,
      carryOverCount: 2
    })
  })

  it('open=false 时不渲染主体', () => {
    const wrapper = mount(DaySummaryPanel, {
      props: { open: false },
      global: {
        stubs: {
          teleport: true,
          transition: false
        }
      }
    })
    expect(wrapper.find('.summary-shell').exists()).toBe(false)
  })

  it('正确展示 completed / pending / 明日首任务，并触发 close 与 preload 事件', async () => {
    const wrapper = mount(DaySummaryPanel, {
      props: { open: true },
      global: {
        stubs: {
          teleport: true,
          transition: false
        }
      }
    })

    expect(wrapper.text()).toContain('战报汇总')
    expect(wrapper.text()).toContain('完成任务 A')
    expect(wrapper.text()).toContain('未完成任务')
    expect(wrapper.text()).toContain('已顺延 x2')
    expect(wrapper.text()).toContain('明日首任务')

    await wrapper.find('button.preload-btn').trigger('click')
    expect(wrapper.emitted('preload-seed-task')?.[0]).toEqual(['todo-1'])

    await wrapper.find('button.close-btn').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
