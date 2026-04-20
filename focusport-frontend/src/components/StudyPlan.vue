<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { planApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const plans = ref([])
const isLoading = ref(false)
const showCreateModal = ref(false)

const newPlan = ref({
  title: '',
  description: '',
  start_date: '',
  end_date: '',
  stages: [{ title: '', description: '' }]
})

const addStage = () => {
  newPlan.value.stages.push({ title: '', description: '' })
}

const removeStage = (index) => {
  if (newPlan.value.stages.length > 1) {
    newPlan.value.stages.splice(index, 1)
  }
}

const loadPlans = async () => {
  isLoading.value = true
  try {
    const res = await planApi.list(userStore.username)
    const planList = res.data.plans || []
    // Load details for each plan to get stages
    const detailed = await Promise.all(
      planList.map(async (p) => {
        try {
          const detail = await planApi.detail(p.id)
          return detail.data.plan || p
        } catch {
          return p
        }
      })
    )
    plans.value = detailed
  } catch (error) {
    console.error('加载计划失败:', error)
  } finally {
    isLoading.value = false
  }
}

const createPlan = async () => {
  if (!newPlan.value.title.trim()) return

  try {
    await planApi.create({
      username: userStore.username,
      ...newPlan.value
    })
    showCreateModal.value = false
    newPlan.value = {
      title: '',
      description: '',
      start_date: '',
      end_date: '',
      stages: [{ title: '', description: '' }]
    }
    await loadPlans()
    alert('计划创建成功！')
  } catch (error) {
    alert('创建失败: ' + (error.response?.data?.detail || error.message))
  }
}

const toggleStage = async (planId, stageId, completed) => {
  try {
    await planApi.updateStage(planId, stageId, { status: completed ? 'pending' : 'completed' })
    await loadPlans()
  } catch (error) {
    console.error('更新进度失败:', error)
  }
}

const deletePlan = async (planId) => {
  if (!confirm('确定要删除这个计划吗？')) return
  try {
    await planApi.delete(planId, userStore.username)
    await loadPlans()
  } catch (error) {
    alert('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const getProgressPercent = (plan) => {
  if (!plan.stages || plan.stages.length === 0) return 0
  const completed = plan.stages.filter(s => s.status === 'completed').length
  return Math.round(completed / plan.stages.length * 100)
}

const goBack = () => router.push('/')

onMounted(() => loadPlans())
</script>

<template>
  <div class="plan-container">
    <div class="plan-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>📚 学习计划</h1>
      <button class="add-btn" @click="showCreateModal = true">+ 新建</button>
    </div>

    <div class="plans-list">
      <div v-for="plan in plans" :key="plan.id" class="plan-card">
        <div class="plan-header-row">
          <h3 class="plan-title">{{ plan.title }}</h3>
          <div class="plan-actions">
            <span :class="['plan-status', plan.status]">{{ plan.status }}</span>
            <button class="delete-plan-btn" @click="deletePlan(plan.id)">🗑️</button>
          </div>
        </div>

        <p class="plan-desc" v-if="plan.description">{{ plan.description }}</p>

        <div class="plan-dates">
          <span>📅 {{ plan.start_date }}</span>
          <span v-if="plan.end_date"> → {{ plan.end_date }}</span>
        </div>

        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: getProgressPercent(plan) + '%' }"></div>
          <span class="progress-text">{{ getProgressPercent(plan) }}%</span>
        </div>

        <div class="stages-list">
          <div
            v-for="stage in plan.stages"
            :key="stage.id"
            :class="['stage-item', { completed: stage.status === 'completed' }]"
          >
            <button
              class="stage-check"
              @click="toggleStage(plan.id, stage.id, stage.status === 'completed')"
            >
              {{ stage.status === 'completed' ? '✅' : '⬜' }}
            </button>
            <div class="stage-info">
              <span class="stage-title">{{ stage.title }}</span>
              <span class="stage-desc" v-if="stage.description">{{ stage.description }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="plans.length === 0" class="empty-state">
        <div class="empty-icon">📝</div>
        <p>还没有学习计划</p>
        <button class="create-btn" @click="showCreateModal = true">创建第一个计划</button>
      </div>
    </div>

    <!-- 创建计划弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <h3>创建学习计划</h3>

        <div class="form-group">
          <label>计划标题</label>
          <input v-model="newPlan.title" type="text" placeholder="例如：完成高数复习" />
        </div>

        <div class="form-group">
          <label>描述（可选）</label>
          <textarea v-model="newPlan.description" placeholder="详细描述你的学习目标..."></textarea>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>开始日期</label>
            <input v-model="newPlan.start_date" type="date" />
          </div>
          <div class="form-group">
            <label>结束日期</label>
            <input v-model="newPlan.end_date" type="date" />
          </div>
        </div>

        <div class="stages-section">
          <label>学习阶段</label>
          <div v-for="(stage, index) in newPlan.stages" :key="index" class="stage-input">
            <input v-model="stage.title" type="text" :placeholder="'阶段 ' + (index + 1)" />
            <button class="remove-stage-btn" @click="removeStage(index)" v-if="newPlan.stages.length > 1">×</button>
          </div>
          <button class="add-stage-btn" @click="addStage">+ 添加阶段</button>
        </div>

        <div class="modal-actions">
          <button @click="showCreateModal = false">取消</button>
          <button class="primary" @click="createPlan">创建计划</button>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.plan-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  color: white;
}

.plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  margin-bottom: 20px;
}

.back-btn, .add-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
}

.add-btn {
  background: rgba(74, 222, 128, 0.25);
  border-color: rgba(74, 222, 128, 0.4);
}

h1 { margin: 0; font-size: 24px; }

.plans-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 20px;
}

.plan-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.plan-title {
  margin: 0;
  font-size: 18px;
}

.plan-status {
  padding: 4px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.plan-status.active { background: rgba(74, 222, 128, 0.25); color: #4ade80; }
.plan-status.completed { background: rgba(59, 130, 246, 0.25); color: #60a5fa; }
.plan-status.paused { background: rgba(251, 191, 36, 0.25); color: #fbbf24; }

.plan-actions { display: flex; align-items: center; gap: 8px; }

.delete-plan-btn {
  background: rgba(248, 113, 113, 0.15);
  border: none;
  border-radius: 8px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.2s;
}

.plan-card:hover .delete-plan-btn { opacity: 1; }
.delete-plan-btn:hover { background: rgba(248, 113, 113, 0.3); }

.plan-desc {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  margin: 0 0 12px 0;
}

.plan-dates {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 16px;
}

.progress-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ade80, #22d3ee);
  border-radius: 4px;
  transition: width 0.5s;
}

.progress-text {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  font-weight: 600;
}

.stages-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.stage-item.completed {
  background: rgba(74, 222, 128, 0.1);
}

.stage-check {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
}

.stage-info { flex: 1; }

.stage-title {
  display: block;
  font-size: 14px;
  font-weight: 500;
}

.stage-desc {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 2px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state p {
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 20px;
}

.create-btn {
  background: rgba(74, 222, 128, 0.25);
  border: 1px solid rgba(74, 222, 128, 0.4);
  color: white;
  padding: 12px 24px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 15px;
}

.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: rgba(30, 40, 60, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 24px;
  width: 420px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content h3 { margin: 0 0 20px 0; }

.form-group { margin-bottom: 16px; }

.form-group label {
  display: block;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 6px;
}

.form-group input, .form-group textarea {
  width: 100%;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  color: white;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group { flex: 1; }

.stages-section { margin-bottom: 16px; }

.stages-section > label {
  display: block;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;
}

.stage-input {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.stage-input input { flex: 1; }

.remove-stage-btn {
  width: 36px;
  height: 36px;
  background: rgba(248, 113, 113, 0.25);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 18px;
  cursor: pointer;
}

.add-stage-btn {
  width: 100%;
  padding: 10px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px dashed rgba(255, 255, 255, 0.3);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  font-size: 13px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.modal-actions button {
  flex: 1;
  padding: 12px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  font-size: 14px;
}

.modal-actions button.primary {
  background: rgba(74, 222, 128, 0.3);
  color: white;
}

.loading-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.spinner {
  width: 40px; height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
