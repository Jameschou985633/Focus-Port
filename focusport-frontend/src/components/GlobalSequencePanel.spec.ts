/* @vitest-environment jsdom */
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'
import GlobalSequencePanel from './GlobalSequencePanel.vue'

const storeState = reactive({
  previewGoal: '',
  decomposeStyle: 'balanced',
  isGenerating: false,
  generationError: '',
  preflightDraft: []
})

const requestAIPreview = vi.fn(async () => {
  mockedStore.preflightDraft = [
    {
      id: 'step-1',
      title: '高数：重做错题 1-8',
      estimatedPomodoros: 2,
      priority: 1,
      reason: '先修复高频错题',
      doneDefinition: '完成 1-8 题重做并标注错因'
    }
  ]
  return mockedStore.preflightDraft
})
const confirmDraftToTimeline = vi.fn(() => ['timeline-1'])
const addDraftItem = vi.fn()
const removeDraftItem = vi.fn()
const moveDraftItem = vi.fn()
const updateDraftItem = vi.fn()

const mockedStore = reactive({
  previewGoal: '',
  decomposeStyle: 'balanced',
  isGenerating: false,
  generationError: '',
  preflightDraft: [],
  requestAIPreview,
  confirmDraftToTimeline,
  addDraftItem,
  removeDraftItem,
  moveDraftItem,
  updateDraftItem
})

vi.mock('../stores/masterTimeline', () => ({
  useMasterTimelineStore: () => mockedStore
}))

describe('GlobalSequencePanel', () => {
  beforeEach(() => {
    storeState.previewGoal = '复习高数'
    storeState.decomposeStyle = 'balanced'
    storeState.isGenerating = false
    storeState.generationError = ''
    storeState.preflightDraft = []
    mockedStore.previewGoal = storeState.previewGoal
    mockedStore.decomposeStyle = storeState.decomposeStyle
    mockedStore.isGenerating = storeState.isGenerating
    mockedStore.generationError = storeState.generationError
    mockedStore.preflightDraft = storeState.preflightDraft
    requestAIPreview.mockClear()
    confirmDraftToTimeline.mockClear()
    addDraftItem.mockClear()
    removeDraftItem.mockClear()
    moveDraftItem.mockClear()
    updateDraftItem.mockClear()
  })

  it('AI 拆解后展示结构化草稿，未确认前不写 timeline', async () => {
    const wrapper = mount(GlobalSequencePanel)
    await wrapper.find('button.sequence-btn.primary').trigger('click')

    expect(requestAIPreview).toHaveBeenCalledTimes(1)
    expect(confirmDraftToTimeline).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('完成标准')
    expect(wrapper.text()).toContain('原因')
  })

  it('确认部署后才触发 draft-deployed 事件', async () => {
    const wrapper = mount(GlobalSequencePanel)
    await wrapper.find('button.sequence-btn.primary').trigger('click')
    await wrapper.find('button.sequence-btn.confirm').trigger('click')

    expect(confirmDraftToTimeline).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('draft-deployed')).toHaveLength(1)
  })
})
