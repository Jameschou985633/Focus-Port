<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { addDays, differenceInCalendarDays, format, startOfWeek } from 'date-fns'
import { useUserStore } from '../stores/user'
import { useFocusHubStore } from '../stores/focusHub'
import P0PilotPanel from './P0PilotPanel.vue'

const router = useRouter()
const userStore = useUserStore()
const focusHubStore = useFocusHubStore()

const isMacroOpen = ref(false)
const showArchive = ref(false)
const newTaskTitle = ref('')
const countdownTitle = ref('')
const countdownDate = ref('')
const showHubSettlement = ref(false)
const hubSessionLog = ref('')
const isHubSettling = ref(false)
const enableP0Pilot = import.meta.env.VITE_ENABLE_P0_PILOT === 'true'

const durationOptions = [15, 25, 30, 45, 60]

const formattedTimer = computed(() => {
  const total = Math.max(0, Number(focusHubStore.pomodoro.remainingSeconds) || 0)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const phaseLabel = computed(() => (
  focusHubStore.pomodoro.mode === 'break' ? 'Recovery Window' : 'Focus Session'
))

const phaseDescription = computed(() => (
  focusHubStore.pomodoro.mode === 'break'
    ? `${focusHubStore.pomodoro.breakMinutes} min tactical reset`
    : `${focusHubStore.pomodoro.focusMinutes} min deep work loop`
))

const totalPhaseSeconds = computed(() => (
  focusHubStore.pomodoro.mode === 'break'
    ? focusHubStore.pomodoro.breakMinutes * 60
    : focusHubStore.pomodoro.focusMinutes * 60
))

const progressRatio = computed(() => {
  if (!totalPhaseSeconds.value) return 0
  return Math.min(1, Math.max(0, 1 - (focusHubStore.pomodoro.remainingSeconds / totalPhaseSeconds.value)))
})

const circleCircumference = 2 * Math.PI * 92
const circleOffset = computed(() => circleCircumference * (1 - progressRatio.value))

const completedTasks = computed(() => focusHubStore.completedTaskCount)
const totalTasks = computed(() => focusHubStore.todayTasks.length)

const weekDays = computed(() => {
  const start = startOfWeek(new Date(), { weekStartsOn: 1 })
  const today = format(new Date(), 'yyyy-MM-dd')

  return Array.from({ length: 7 }, (_, index) => {
    const date = addDays(start, index)
    const dateKey = format(date, 'yyyy-MM-dd')
    return {
      dateKey,
      label: format(date, 'EEE'),
      dayNumber: format(date, 'dd'),
      monthLabel: format(date, 'MM'),
      isToday: dateKey === today,
      notes: focusHubStore.getNotesForDate(dateKey)
    }
  })
})

const countdownCards = computed(() => (
  [...focusHubStore.countdowns].sort((left, right) => String(left.targetDate).localeCompare(String(right.targetDate)))
))

const goBack = () => {
  router.push('/more')
}

const submitTask = () => {
  if (focusHubStore.addTask(newTaskTitle.value)) {
    newTaskTitle.value = ''
  }
}

const submitCountdown = () => {
  if (focusHubStore.addCountdown(countdownTitle.value, countdownDate.value)) {
    countdownTitle.value = ''
    countdownDate.value = ''
  }
}

const handleWeekNoteChange = (dateKey, noteIndex, event) => {
  focusHubStore.updateWeekNote(dateKey, noteIndex, event.target.value)
}

const countdownStatus = (targetDate) => {
  const delta = differenceInCalendarDays(new Date(targetDate), new Date())
  if (delta > 0) return `D-${delta}`
  if (delta === 0) return 'Today'
  return `已过 ${Math.abs(delta)} 天`
}

const countdownTone = (targetDate) => {
  const delta = differenceInCalendarDays(new Date(targetDate), new Date())
  if (delta < 0) return 'expired'
  if (delta === 0) return 'today'
  if (delta <= 3) return 'warning'
  return 'normal'
}

onMounted(() => {
  focusHubStore.hydrate(userStore.username)
})

watch(() => focusHubStore.pomodoro.pendingSettlement, (pending) => {
  if (pending) {
    showHubSettlement.value = true
    hubSessionLog.value = ''
  }
})

const submitHubSettlement = async () => {
  if (isHubSettling.value) return
  isHubSettling.value = true
  try {
    await focusHubStore.completeFocusSession({
      username: userStore.username,
      duration: focusHubStore.pomodoro.focusMinutes,
      subject: '自律中枢番茄钟',
      sessionLog: hubSessionLog.value,
      taskDifficulty: focusHubStore.pomodoro.taskDifficulty
    })
    focusHubStore.resolveFocusCompletion()
    showHubSettlement.value = false
  } catch (error) {
    console.error('Hub settlement failed', error)
    window.alert('结算失败，请稍后再试。')
  } finally {
    isHubSettling.value = false
  }
}

const skipHubSettlement = () => {
  focusHubStore.skipSettlement()
  showHubSettlement.value = false
}
</script>

<template>
  <div class="focus-hub-page">
    <div class="space-grid"></div>
    <div class="scanline"></div>

    <div class="hub-shell">
      <header class="hub-header card glass-dark animate-slide-down">
        <div class="header-copy">
          <p class="eyebrow">FocusPort / Self-Discipline Nexus</p>
          <h1>自律中枢</h1>
          <p class="header-subtitle">
            保持今天的工作界面干净可控，把专注、任务与关键节点压缩到一块面板里。
          </p>
        </div>

        <div class="header-actions">
          <button type="button" class="hub-btn ghost" @click="goBack">返回中控</button>
          <button
            type="button"
            class="hub-btn accent"
            :aria-expanded="isMacroOpen"
            @click="isMacroOpen = !isMacroOpen"
          >
            {{ isMacroOpen ? '收起宏观层' : '展开宏观层' }}
          </button>
        </div>
      </header>

      <P0PilotPanel v-if="enableP0Pilot" />

      <section class="macro-drawer card glass animate-fade-in" :class="{ open: isMacroOpen }">
        <div class="drawer-head">
          <div>
            <p class="eyebrow">Macro Overlay</p>
            <h2>周节点与倒数日</h2>
          </div>
          <span class="drawer-state">{{ isMacroOpen ? 'ONLINE' : 'STANDBY' }}</span>
        </div>

        <div class="drawer-body">
          <div class="macro-grid">
            <div class="macro-column">
              <div class="section-head">
                <h3>本周节点</h3>
                <p>每一天最多 2 条关键节点。</p>
              </div>

              <div class="week-strip">
                <article
                  v-for="day in weekDays"
                  :key="day.dateKey"
                  class="day-card"
                  :class="{ today: day.isToday }"
                >
                  <div class="day-topline">
                    <div>
                      <p class="day-label">{{ day.label }}</p>
                      <strong>{{ day.dayNumber }}</strong>
                    </div>
                    <span>{{ day.monthLabel }}</span>
                  </div>

                  <div class="node-list">
                    <div
                      v-for="(note, noteIndex) in day.notes"
                      :key="`${day.dateKey}-${noteIndex}`"
                      class="node-row"
                    >
                      <input
                        class="node-input"
                        :value="note"
                        maxlength="28"
                        placeholder="输入节点"
                        @change="handleWeekNoteChange(day.dateKey, noteIndex, $event)"
                      />
                      <button
                        type="button"
                        class="icon-btn"
                        aria-label="删除节点"
                        @click="focusHubStore.deleteWeekNote(day.dateKey, noteIndex)"
                      >
                        ×
                      </button>
                    </div>
                  </div>

                  <button
                    v-if="day.notes.length < 2"
                    type="button"
                    class="mini-link"
                    @click="focusHubStore.addWeekNote(day.dateKey)"
                  >
                    + 添加节点
                  </button>
                </article>
              </div>
            </div>

            <div class="macro-column">
              <div class="section-head">
                <h3>倒数日</h3>
                <p>用来盯住上线、DDL 或考试节点。</p>
              </div>

              <form class="countdown-form" @submit.prevent="submitCountdown">
                <input
                  v-model="countdownTitle"
                  class="input"
                  maxlength="36"
                  placeholder="例如：产品上线"
                />
                <input v-model="countdownDate" class="input" type="date" />
                <button type="submit" class="hub-btn success">添加</button>
              </form>

              <div v-if="countdownCards.length" class="countdown-list">
                <article
                  v-for="item in countdownCards"
                  :key="item.id"
                  class="countdown-card"
                  :class="countdownTone(item.targetDate)"
                >
                  <div>
                    <p class="countdown-title">{{ item.title }}</p>
                    <p class="countdown-date-label">{{ item.targetDate }}</p>
                  </div>
                  <div class="countdown-meta">
                    <strong>{{ countdownStatus(item.targetDate) }}</strong>
                    <button
                      type="button"
                      class="icon-btn"
                      aria-label="删除倒数日"
                      @click="focusHubStore.deleteCountdown(item.id)"
                    >
                      ×
                    </button>
                  </div>
                </article>
              </div>

              <div v-else class="empty-block">
                <p>还没有倒数目标。</p>
                <span>把真正重要的时间点抛到这里，主面板才能更专注。</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <main class="hub-main">
        <section class="pomodoro-panel card glass-strong animate-slide-up">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Pomodoro Engine</p>
              <h2>{{ phaseLabel }}</h2>
            </div>
            <span class="status-pill" :class="{ break: focusHubStore.pomodoro.mode === 'break' }">
              {{ focusHubStore.pomodoro.isRunning ? 'RUNNING' : 'PAUSED' }}
            </span>
          </div>

          <div v-if="focusHubStore.pomodoro.mode !== 'break'" class="hub-duration-pills">
            <button
              v-for="m in durationOptions"
              :key="m"
              type="button"
              class="hub-pill"
              :class="{ active: focusHubStore.pomodoro.focusMinutes === m }"
              :disabled="focusHubStore.pomodoro.isRunning"
              @click="focusHubStore.setFocusMinutes(m)"
            >
              {{ m }}m
            </button>
          </div>

          <div v-if="focusHubStore.pomodoro.mode !== 'break'" class="hub-difficulty-row">
            <button
              type="button"
              class="hub-diff-btn"
              :class="{ active: focusHubStore.pomodoro.taskDifficulty === 'L1' }"
              :disabled="focusHubStore.pomodoro.isRunning"
              @click="focusHubStore.setTaskDifficulty('L1')"
            >
              L1 日常
            </button>
            <button
              type="button"
              class="hub-diff-btn"
              :class="{ active: focusHubStore.pomodoro.taskDifficulty === 'L2' }"
              :disabled="focusHubStore.pomodoro.isRunning"
              @click="focusHubStore.setTaskDifficulty('L2')"
            >
              L2 硬核
            </button>
          </div>

          <div v-if="focusHubStore.pomodoro.linkedTaskTitle" class="linked-task-chip">
            <span>关联任务</span>
            <strong>{{ focusHubStore.pomodoro.linkedTaskTitle }}</strong>
          </div>

          <div class="timer-stage">
            <svg class="progress-ring" viewBox="0 0 240 240" aria-hidden="true">
              <defs>
                <linearGradient v-if="focusHubStore.pomodoro.mode !== 'break'" id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#5ce3ff" />
                  <stop offset="100%" stop-color="#63ffad" />
                </linearGradient>
                <linearGradient v-else id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#ffb757" />
                  <stop offset="100%" stop-color="#ff7147" />
                </linearGradient>
              </defs>
              <circle class="ring-base" cx="120" cy="120" r="92" />
              <circle
                class="ring-progress"
                cx="120"
                cy="120"
                r="92"
                :stroke-dasharray="circleCircumference"
                :stroke-dashoffset="circleOffset"
              />
            </svg>

            <div class="timer-copy">
              <p class="mode-caption">{{ phaseDescription }}</p>
              <strong class="timer-value">{{ formattedTimer }}</strong>
              <span class="timer-progress">{{ Math.round(progressRatio * 100) }}% complete</span>
            </div>
          </div>

          <div class="pomodoro-stats">
            <div class="stat-chip">
              <span>今日完成轮次</span>
              <strong>{{ focusHubStore.pomodoro.completedFocusSessions }}</strong>
            </div>
            <div class="stat-chip">
              <span>当前节奏</span>
              <strong>{{ focusHubStore.pomodoro.focusMinutes }} / {{ focusHubStore.pomodoro.breakMinutes }}</strong>
            </div>
          </div>

          <div class="pomodoro-actions">
            <button
              v-if="!focusHubStore.pomodoro.isRunning"
              type="button"
              class="hub-btn success large"
              @click="focusHubStore.startPomodoro()"
            >
              开始
            </button>
            <button
              v-else
              type="button"
              class="hub-btn warning large"
              @click="focusHubStore.pausePomodoro()"
            >
              暂停
            </button>
            <button
              type="button"
              class="hub-btn ghost large"
              @click="focusHubStore.resetPomodoro()"
            >
              重置
            </button>
          </div>
        </section>

        <!-- Hub settlement modal -->
        <div v-if="showHubSettlement" class="hub-settle-overlay">
          <div class="hub-settle-card">
            <h3>专注完成</h3>
            <p>本轮 {{ focusHubStore.pomodoro.focusMinutes }} 分钟 · 难度 {{ focusHubStore.pomodoro.taskDifficulty }}</p>
            <textarea
              v-model="hubSessionLog"
              class="hub-settle-input"
              placeholder="写一句日志记录本轮做了什么（可留空）"
              :disabled="isHubSettling"
            />
            <div class="hub-settle-actions">
              <button
                type="button"
                class="hub-btn primary large"
                :disabled="isHubSettling"
                @click="submitHubSettlement"
              >
                {{ isHubSettling ? '结算中...' : '提交结算' }}
              </button>
              <button
                type="button"
                class="hub-btn ghost large"
                :disabled="isHubSettling"
                @click="skipHubSettlement"
              >
                跳过
              </button>
            </div>
          </div>
        </div>

        <section class="tasks-panel card glass animate-slide-up">
          <div class="panel-head">
            <div>
              <p class="eyebrow">Daily Tasks</p>
              <h2>今日任务</h2>
            </div>
            <div class="task-summary">
              <strong>{{ completedTasks }}/{{ totalTasks || 0 }}</strong>
              <span>done today</span>
            </div>
          </div>

          <form class="task-entry" @submit.prevent="submitTask">
            <input
              v-model="newTaskTitle"
              class="input"
              maxlength="72"
              placeholder="输入任务后回车，例如：完成发布页交互稿"
            />
            <button type="submit" class="hub-btn primary">录入</button>
          </form>

          <div v-if="focusHubStore.todayTasks.length" class="task-list">
            <article
              v-for="task in focusHubStore.todayTasks"
              :key="task.id"
              class="task-row"
              :class="{ completed: task.completed }"
            >
              <button
                type="button"
                class="check-btn"
                :aria-pressed="task.completed"
                @click="focusHubStore.toggleTask(task.id)"
              >
                <span>{{ task.completed ? '✓' : '' }}</span>
              </button>

              <div class="task-copy">
                <div class="task-title-line">
                  <p class="task-title">{{ task.title }}</p>
                  <span v-if="task.isDeferred" class="deferred-badge">
                    延期 {{ task.deferredCount }}d
                  </span>
                </div>
                <p class="task-meta">
                  创建于 {{ task.createdAt.slice(0, 10) }}
                  <span v-if="task.deferredFrom"> · 来自 {{ task.deferredFrom }}</span>
                </p>
              </div>

              <button
                type="button"
                class="icon-btn danger"
                aria-label="删除任务"
                @click="focusHubStore.deleteTask(task.id)"
              >
                ×
              </button>
            </article>
          </div>

          <div v-else class="empty-block task-empty">
            <p>今天的任务面板还是空的。</p>
            <span>先把最重要的一件事丢进来，再启动番茄钟。</span>
          </div>

          <div class="archive-box">
            <button type="button" class="archive-toggle" @click="showArchive = !showArchive">
              <span>历史归档</span>
              <strong>{{ focusHubStore.archiveTasks.length }}</strong>
            </button>

            <div v-if="showArchive" class="archive-list">
              <article
                v-for="item in focusHubStore.archiveTasks.slice(0, 8)"
                :key="`${item.id}-${item.archivedOn}`"
                class="archive-row"
              >
                <div>
                  <p>{{ item.title }}</p>
                  <span>{{ item.archivedOn }} archived</span>
                </div>
                <strong>{{ item.completedAt ? item.completedAt.slice(0, 10) : 'done' }}</strong>
              </article>

              <div v-if="!focusHubStore.archiveTasks.length" class="archive-empty">
                还没有历史记录。
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.focus-hub-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(48, 212, 255, 0.16), transparent 30%),
    radial-gradient(circle at top right, rgba(86, 255, 155, 0.14), transparent 25%),
    linear-gradient(180deg, #07111f 0%, #091523 38%, #030812 100%);
  color: var(--color-text-primary);
}

.space-grid,
.scanline {
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.space-grid {
  background-image:
    linear-gradient(rgba(72, 183, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(72, 183, 255, 0.08) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: radial-gradient(circle at center, black 55%, transparent 100%);
  opacity: 0.28;
}

.scanline {
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.02) 0%,
    transparent 18%,
    transparent 52%,
    rgba(255, 255, 255, 0.02) 100%
  );
  mix-blend-mode: screen;
}

.hub-shell {
  position: relative;
  z-index: 1;
  width: min(1360px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 40px;
}

.hub-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  margin-bottom: 18px;
  border-radius: 28px;
}

.header-copy h1 {
  margin: 8px 0 12px;
  font-size: clamp(34px, 5vw, 56px);
  line-height: 0.95;
  letter-spacing: 0.04em;
}

.header-subtitle {
  max-width: 620px;
  color: rgba(219, 238, 255, 0.74);
}

.eyebrow {
  margin: 0;
  color: #83e7ff;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.header-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.macro-drawer {
  padding: 0;
  margin-bottom: 18px;
  border-radius: 28px;
  overflow: hidden;
}

.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px;
}

.drawer-head h2,
.panel-head h2 {
  margin: 6px 0 0;
  font-size: 28px;
}

.drawer-state {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(95, 231, 255, 0.26);
  color: #9ef8ff;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.12em;
}

.drawer-body {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 220ms ease;
}

.macro-drawer.open .drawer-body {
  grid-template-rows: 1fr;
}

.macro-grid {
  min-height: 0;
  overflow: hidden;
}

.macro-drawer.open .macro-grid {
  padding: 0 24px 24px;
}

.macro-column + .macro-column {
  margin-top: 20px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head h3 {
  margin: 0;
  font-size: 18px;
}

.section-head p {
  margin: 0;
  color: rgba(219, 238, 255, 0.58);
  font-size: 13px;
}

.week-strip {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
}

.day-card {
  min-height: 184px;
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(8, 29, 53, 0.94), rgba(4, 12, 28, 0.98));
  border: 1px solid rgba(95, 231, 255, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.day-card.today {
  border-color: rgba(95, 231, 255, 0.45);
  box-shadow: 0 0 0 1px rgba(95, 231, 255, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.day-topline {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}

.day-label {
  margin: 0 0 4px;
  color: rgba(219, 238, 255, 0.55);
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.14em;
}

.day-topline strong {
  font-size: 26px;
}

.day-topline span {
  color: rgba(219, 238, 255, 0.56);
  font-family: var(--font-mono);
}

.node-list {
  display: grid;
  gap: 10px;
}

.node-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
}

.node-input {
  width: 100%;
  min-width: 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(95, 231, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #f6fbff;
  font-size: 13px;
}

.node-input:focus {
  outline: none;
  border-color: rgba(95, 231, 255, 0.45);
  box-shadow: 0 0 0 3px rgba(72, 183, 255, 0.12);
}

.mini-link {
  margin-top: 12px;
  border: none;
  background: transparent;
  color: #7ddcf8;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}

.countdown-form,
.task-entry {
  display: grid;
  grid-template-columns: 1.4fr 0.9fr auto;
  gap: 12px;
}

.countdown-list {
  margin-top: 14px;
  display: grid;
  gap: 12px;
}

.countdown-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(95, 231, 255, 0.16);
  background: rgba(255, 255, 255, 0.04);
}

.countdown-card.warning,
.countdown-card.today {
  border-color: rgba(255, 183, 85, 0.36);
}

.countdown-card.expired {
  border-color: rgba(255, 113, 113, 0.24);
}

.countdown-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}

.countdown-date-label {
  margin: 0;
  color: rgba(219, 238, 255, 0.58);
  font-size: 12px;
}

.countdown-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.countdown-meta strong {
  font-size: 24px;
  color: #ffcf7f;
  white-space: nowrap;
}

.countdown-card.normal .countdown-meta strong {
  color: #86f2ff;
}

.countdown-card.expired .countdown-meta strong {
  color: #ff9292;
}

.empty-block {
  padding: 24px;
  border-radius: 18px;
  border: 1px dashed rgba(95, 231, 255, 0.16);
  background: rgba(255, 255, 255, 0.025);
  color: rgba(219, 238, 255, 0.72);
}

.empty-block p {
  margin: 0 0 8px;
  font-size: 15px;
}

.empty-block span {
  color: rgba(219, 238, 255, 0.5);
  font-size: 13px;
}

.hub-main {
  display: grid;
  grid-template-columns: minmax(320px, 0.4fr) minmax(380px, 0.6fr);
  gap: 18px;
}

.pomodoro-panel,
.tasks-panel {
  padding: 24px;
  border-radius: 28px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}

.status-pill,
.task-summary {
  padding: 10px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(95, 231, 255, 0.16);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.08em;
}

.status-pill.break {
  border-color: rgba(255, 183, 85, 0.28);
  color: #ffd08d;
}

.task-summary {
  text-align: right;
}

.task-summary strong {
  display: block;
  font-size: 22px;
}

.task-summary span {
  color: rgba(219, 238, 255, 0.5);
}

.timer-stage {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 360px;
}

.progress-ring {
  width: min(100%, 320px);
  aspect-ratio: 1;
  transform: rotate(-90deg);
  filter: drop-shadow(0 0 20px rgba(72, 183, 255, 0.2));
}

.ring-base,
.ring-progress {
  fill: none;
  stroke-width: 10;
}

.ring-base {
  stroke: rgba(255, 255, 255, 0.08);
}

.ring-progress {
  stroke: url(#ringGradient);
  stroke-linecap: round;
  transition: stroke-dashoffset 320ms linear;
}

.timer-copy {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 56px;
}

.mode-caption {
  margin: 0 0 10px;
  color: rgba(219, 238, 255, 0.55);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 11px;
}

.timer-value {
  display: block;
  font-size: clamp(56px, 8vw, 78px);
  letter-spacing: 0.08em;
  font-family: var(--font-mono);
  text-shadow: 0 0 24px rgba(95, 231, 255, 0.2);
}

.timer-progress {
  margin-top: 10px;
  color: rgba(219, 238, 255, 0.58);
  font-size: 13px;
}

.pomodoro-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.stat-chip {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(95, 231, 255, 0.12);
}

.stat-chip span {
  display: block;
  color: rgba(219, 238, 255, 0.52);
  font-size: 12px;
  margin-bottom: 6px;
}

.stat-chip strong {
  font-size: 20px;
}

.pomodoro-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.task-entry {
  margin-bottom: 18px;
  grid-template-columns: 1fr auto;
}

.task-list {
  display: grid;
  gap: 12px;
}

.task-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(95, 231, 255, 0.1);
}

.task-row.completed {
  opacity: 0.72;
  border-color: rgba(99, 255, 173, 0.18);
}

.task-row.completed .task-title {
  text-decoration: line-through;
  color: rgba(219, 238, 255, 0.58);
}

.check-btn {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: 1px solid rgba(95, 231, 255, 0.24);
  background: rgba(255, 255, 255, 0.04);
  color: #63ffad;
  display: grid;
  place-items: center;
  cursor: pointer;
  font-weight: 800;
}

.task-copy {
  min-width: 0;
}

.task-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.task-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  word-break: break-word;
}

.task-meta {
  margin: 6px 0 0;
  color: rgba(219, 238, 255, 0.48);
  font-size: 12px;
}

.deferred-badge {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 183, 85, 0.12);
  border: 1px solid rgba(255, 183, 85, 0.28);
  color: #ffc886;
  font-size: 11px;
  letter-spacing: 0.06em;
}

.archive-box {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.archive-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(95, 231, 255, 0.12);
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  cursor: pointer;
}

.archive-list {
  margin-top: 12px;
  display: grid;
  gap: 10px;
}

.archive-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
}

.archive-row p,
.archive-row span,
.archive-row strong {
  margin: 0;
}

.archive-row span {
  color: rgba(219, 238, 255, 0.46);
  font-size: 12px;
}

.archive-row strong {
  color: rgba(219, 238, 255, 0.6);
  font-family: var(--font-mono);
  font-size: 12px;
}

.archive-empty {
  padding: 12px 14px;
  border-radius: 14px;
  color: rgba(219, 238, 255, 0.5);
  background: rgba(255, 255, 255, 0.02);
}

.hub-btn,
.icon-btn,
.check-btn,
.archive-toggle {
  border: 1px solid transparent;
  cursor: pointer;
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

.hub-btn:hover,
.icon-btn:hover,
.check-btn:hover,
.archive-toggle:hover {
  transform: translateY(-1px);
}

.hub-btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  color: #f6fbff;
  font-size: 14px;
  font-weight: 700;
}

.hub-btn.large {
  min-height: 50px;
}

.hub-btn.primary {
  background: linear-gradient(135deg, rgba(54, 192, 255, 0.26), rgba(53, 122, 255, 0.18));
  border-color: rgba(95, 231, 255, 0.24);
}

.hub-btn.accent {
  background: linear-gradient(135deg, rgba(95, 231, 255, 0.18), rgba(99, 255, 173, 0.14));
  border-color: rgba(95, 231, 255, 0.24);
}

.hub-btn.success {
  background: linear-gradient(135deg, rgba(63, 255, 146, 0.28), rgba(34, 197, 94, 0.18));
  border-color: rgba(99, 255, 173, 0.26);
}

.hub-btn.warning {
  background: linear-gradient(135deg, rgba(255, 183, 85, 0.28), rgba(255, 120, 63, 0.16));
  border-color: rgba(255, 183, 85, 0.26);
}

.hub-btn.ghost {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.12);
}

.hub-btn:focus-visible,
.icon-btn:focus-visible,
.check-btn:focus-visible,
.archive-toggle:focus-visible,
.mini-link:focus-visible {
  outline: 2px solid rgba(95, 231, 255, 0.7);
  outline-offset: 2px;
}

.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #e8f8ff;
  display: grid;
  place-items: center;
  font-size: 20px;
  line-height: 1;
}

.icon-btn.danger {
  color: #ff9b9b;
  border-color: rgba(255, 113, 113, 0.2);
}

.hub-duration-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.hub-pill {
  border: none;
  border-radius: 999px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.06);
  color: #dbeeff;
  cursor: pointer;
  font-weight: 700;
  font-size: 13px;
  transition: background 180ms ease, color 180ms ease;
}

.hub-pill.active {
  background: linear-gradient(135deg, rgba(95, 231, 255, 0.28), rgba(99, 255, 173, 0.18));
  border: 1px solid rgba(95, 231, 255, 0.24);
  color: #fff;
}

.hub-pill:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hub-difficulty-row {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.hub-diff-btn {
  flex: 1;
  border: 1px solid rgba(95, 231, 255, 0.16);
  border-radius: 12px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.04);
  color: #dbeeff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  text-align: center;
  transition: background 180ms ease, border-color 180ms ease;
}

.hub-diff-btn.active {
  border-color: rgba(95, 231, 255, 0.42);
  background: linear-gradient(135deg, rgba(54, 192, 255, 0.22), rgba(53, 122, 255, 0.16));
}

.hub-diff-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.linked-task-chip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(99, 255, 173, 0.08);
  border: 1px solid rgba(99, 255, 173, 0.18);
  margin-bottom: 14px;
  font-size: 13px;
}

.linked-task-chip span {
  color: rgba(219, 238, 255, 0.55);
}

.linked-task-chip strong {
  color: #63ffad;
}

.hub-settle-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(2, 6, 18, 0.72);
  backdrop-filter: blur(14px);
}

.hub-settle-card {
  width: min(440px, calc(100vw - 24px));
  border-radius: 24px;
  padding: 24px;
  background:
    linear-gradient(180deg, rgba(16, 34, 74, 0.96), rgba(8, 16, 36, 0.98)),
    rgba(11, 18, 32, 0.92);
  border: 1.5px solid rgba(95, 231, 255, 0.28);
  color: #eef7ff;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hub-settle-card h3 {
  margin: 0;
  font-size: 24px;
}

.hub-settle-card p {
  margin: 0;
  color: rgba(219, 238, 255, 0.68);
}

.hub-settle-input {
  min-height: 100px;
  border: 1px solid rgba(95, 231, 255, 0.18);
  border-radius: 16px;
  background: rgba(7, 14, 32, 0.82);
  color: #eef7ff;
  padding: 12px 14px;
  resize: vertical;
  outline: none;
  font: inherit;
  line-height: 1.6;
}

.hub-settle-actions {
  display: flex;
  gap: 10px;
}

@media (min-width: 1040px) {
  .macro-drawer.open .macro-grid {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 20px;
  }

  .macro-column + .macro-column {
    margin-top: 0;
  }
}

@media (max-width: 1039px) {
  .week-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hub-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .hub-shell {
    width: min(100% - 20px, 100%);
    padding-top: 18px;
  }

  .hub-header {
    padding: 20px;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions .hub-btn {
    flex: 1;
  }

  .macro-drawer.open .macro-grid {
    padding: 0 16px 16px;
  }

  .drawer-head,
  .pomodoro-panel,
  .tasks-panel {
    padding: 18px;
  }

  .week-strip,
  .countdown-form,
  .pomodoro-stats,
  .pomodoro-actions {
    grid-template-columns: 1fr;
  }

  .task-entry {
    grid-template-columns: 1fr;
  }

  .day-card {
    min-height: unset;
  }

  .timer-stage {
    min-height: 300px;
  }

  .timer-copy {
    padding: 36px;
  }
}
</style>
