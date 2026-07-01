/* @vitest-environment jsdom */
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'
import TaskCompleteModal from './TaskCompleteModal.vue'
import type { AIAnalysisPayload } from '../stores/useTaskStore'

const completeTask = vi.fn()
const getTaskById = vi.fn()
const triggerAIAnalysis = vi.fn()

vi.mock('../stores/useTaskStore', () => ({
  useTaskStore: () => ({
    completeTask,
    getTaskById,
    triggerAIAnalysis
  })
}))

describe('TaskCompleteModal', () => {
  const mockPayload: AIAnalysisPayload = {
    score: 86,
    focusLevel: 'A',
    expGained: 12,
    computePowerGained: 25,
    summary: '完成质量稳定。',
    encouragement: '保持这个节奏。',
    multiplier: 1.2,
    distractionDetected: false,
    completionStatus: 'full',
    behaviorTags: []
  }

  beforeEach(() => {
    vi.useFakeTimers()
    completeTask.mockReset()
    getTaskById.mockReset()
    triggerAIAnalysis.mockReset()
    getTaskById.mockReturnValue({
      id: 'task-1',
      completedAt: Date.now(),
      totalFocusSeconds: 1500,
      actualPomodoros: 1
    })
    triggerAIAnalysis.mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(() => resolve(mockPayload), 100)
        })
    )
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('按 form -> loading -> result -> auto-close 流转，并展示关键奖励字段', async () => {
    const wrapper = mount(TaskCompleteModal, {
      props: {
        open: true,
        taskId: 'task-1',
        taskTitle: 'Task 1'
      },
      global: {
        stubs: {
          teleport: true,
          transition: false
        }
      }
    })

    expect(wrapper.text()).toContain('任务完成并结算')
    await wrapper.find('button.primary-btn').trigger('click')
    expect(wrapper.text()).toContain('AI 算力解析中...')

    vi.advanceTimersByTime(100)
    await flushPromises()
    expect(wrapper.text()).toContain('专注等级')
    expect(wrapper.text()).toContain('倍率')
    expect(wrapper.text()).toContain('分心检测')
    expect(wrapper.text()).toContain('+25')
    expect(wrapper.text()).toContain('+12')
  })

  it('auto-close 事件顺序为 reward-trigger -> submitted -> update:open -> close', async () => {
    const eventOrder: string[] = []
    const host = defineComponent({
      components: { TaskCompleteModal },
      setup() {
        const open = ref(true)
        const onReward = () => eventOrder.push('reward-trigger')
        const onSubmitted = () => eventOrder.push('submitted')
        const onUpdateOpen = (value: boolean) => {
          eventOrder.push('update:open')
          open.value = value
        }
        const onClose = () => eventOrder.push('close')
        return { open, onReward, onSubmitted, onUpdateOpen, onClose }
      },
      template: `
        <TaskCompleteModal
          v-model:open="open"
          task-id="task-1"
          task-title="Task 1"
          @reward-trigger="onReward"
          @submitted="onSubmitted"
          @update:open="onUpdateOpen"
          @close="onClose"
        />
      `
    })

    const wrapper = mount(host, {
      global: {
        stubs: {
          teleport: true,
          transition: false
        }
      }
    })

    await wrapper.find('button.primary-btn').trigger('click')
    vi.advanceTimersByTime(100)
    await flushPromises()
    vi.advanceTimersByTime(1200)
    await flushPromises()

    expect(eventOrder).toEqual(['reward-trigger', 'submitted', 'update:open', 'close'])
  })
})
