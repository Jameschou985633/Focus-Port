<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  goal: {
    type: String,
    default: ''
  },
  targetTaskTitle: {
    type: String,
    default: ''
  },
  draftItems: {
    type: Array,
    default: () => []
  },
  isGenerating: {
    type: Boolean,
    default: false
  },
  generationError: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'close',
  'refresh-ai',
  'confirm',
  'add-step',
  'remove-step',
  'move-step',
  'update-step-title',
  'update-step-pomodoros'
])

const editableGoal = ref('')

watch(
  () => props.goal,
  (value) => {
    editableGoal.value = String(value || '')
  },
  { immediate: true }
)

const onEsc = (event) => {
  if (event.key === 'Escape' && props.open) {
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', onEsc)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onEsc)
})
</script>

<template>
  <Teleport to="#focus-overlay-root">
    <transition
      enter-active-class="transition duration-220 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-180 ease-out"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fp-glass-overlay fixed inset-0 z-[170] flex items-center justify-center bg-slate-950/70 px-3 py-6 backdrop-blur-sm"
        @click.self="$emit('close')"
      >
        <transition
          enter-active-class="transition duration-220 ease-out"
          enter-from-class="translate-y-3 opacity-0"
          enter-to-class="translate-y-0 opacity-100"
          leave-active-class="transition duration-180 ease-out"
          leave-from-class="translate-y-0 opacity-100"
          leave-to-class="translate-y-3 opacity-0"
        >
          <section
            v-if="open"
            class="fp-glass-modal fp-glass-modal-wide w-full max-w-4xl rounded-2xl border border-sky-300/30 bg-[#0F1525]/95 p-4 shadow-[0_20px_44px_rgba(2,6,23,0.55)] backdrop-blur-xl md:p-5"
          >
            <header class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-[11px] uppercase tracking-[0.14em] text-sky-200/70">AI Task Decompose</p>
                <h3 class="mt-1 text-xl font-semibold text-slate-100">{{ targetTaskTitle || '未选择主任务' }}</h3>
                <p class="mt-1 text-sm text-slate-300">将主任务拆成可执行阶段，确认后写入 To-do 阶段列表。</p>
              </div>

              <div class="flex items-center gap-2">
                <button
                  type="button"
                  class="rounded-lg border border-indigo-300/45 bg-indigo-500/15 px-3 py-2 text-sm font-semibold text-indigo-100 transition hover:bg-indigo-500/25 disabled:cursor-not-allowed disabled:opacity-55"
                  :disabled="isGenerating"
                  @click="$emit('refresh-ai')"
                >
                  {{ isGenerating ? 'AI拆解中...' : '重新AI拆解' }}
                </button>
                <button
                  type="button"
                  class="grid h-9 w-9 place-items-center rounded-xl border border-sky-300/30 bg-slate-800/80 text-slate-200 transition hover:bg-sky-500/20"
                  @click="$emit('close')"
                >
                  x
                </button>
              </div>
            </header>

            <div class="mt-3 rounded-xl border border-slate-700/70 bg-slate-900/55 p-3">
              <p class="text-xs uppercase tracking-[0.12em] text-slate-400">Goal</p>
              <p class="mt-1 text-sm text-slate-200">{{ editableGoal || '未提供目标文本' }}</p>
            </div>

            <p v-if="generationError" class="mt-3 text-sm text-rose-300">{{ generationError }}</p>

            <div v-if="isGenerating" class="mt-3 space-y-2">
              <div class="h-14 animate-pulse rounded-xl bg-slate-700/60" />
              <div class="h-14 animate-pulse rounded-xl bg-slate-700/50" />
              <div class="h-14 animate-pulse rounded-xl bg-slate-700/40" />
            </div>

            <div v-else class="mt-3 max-h-[48vh] space-y-2 overflow-y-auto pr-1">
              <article
                v-for="(item, index) in draftItems"
                :key="item.id"
                class="rounded-xl border border-slate-700/65 bg-slate-900/55 p-3"
              >
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <span class="rounded-full border border-sky-300/35 bg-sky-500/10 px-2 py-0.5 text-[11px] text-sky-100">阶段 {{ index + 1 }}</span>
                  <div class="flex items-center gap-2 text-xs">
                    <button
                      type="button"
                      class="rounded-md border border-slate-500/50 px-2 py-1 text-slate-200 transition hover:border-slate-300/60 disabled:cursor-not-allowed disabled:opacity-45"
                      :disabled="index === 0"
                      @click="$emit('move-step', { id: item.id, direction: 'up' })"
                    >
                      上移
                    </button>
                    <button
                      type="button"
                      class="rounded-md border border-slate-500/50 px-2 py-1 text-slate-200 transition hover:border-slate-300/60 disabled:cursor-not-allowed disabled:opacity-45"
                      :disabled="index === draftItems.length - 1"
                      @click="$emit('move-step', { id: item.id, direction: 'down' })"
                    >
                      下移
                    </button>
                    <button
                      type="button"
                      class="rounded-md border border-rose-300/45 bg-rose-500/15 px-2 py-1 text-rose-100 transition hover:bg-rose-500/25"
                      @click="$emit('remove-step', item.id)"
                    >
                      删除
                    </button>
                  </div>
                </div>

                <div class="mt-2 grid gap-2 md:grid-cols-[1fr_120px]">
                  <input
                    :value="item.title"
                    type="text"
                    class="min-h-10 rounded-lg border border-slate-600/70 bg-slate-900/75 px-3 text-sm text-slate-100 outline-none transition focus:border-sky-300/55 focus:ring-2 focus:ring-sky-400/20"
                    placeholder="输入阶段动作"
                    @input="$emit('update-step-title', { id: item.id, value: $event.target.value })"
                  >
                  <label class="flex items-center gap-2 rounded-lg border border-slate-600/70 bg-slate-900/75 px-3">
                    <span class="text-xs text-slate-300">番茄</span>
                    <input
                      :value="item.estimatedPomodoros"
                      type="number"
                      min="1"
                      max="3"
                      class="h-8 w-full bg-transparent text-sm text-slate-100 outline-none"
                      @input="$emit('update-step-pomodoros', { id: item.id, value: $event.target.value })"
                    >
                  </label>
                </div>
              </article>

              <div
                v-if="!draftItems.length"
                class="rounded-xl border border-slate-700/70 bg-slate-900/55 p-4 text-sm text-slate-400"
              >
                当前没有可确认的 AI 步骤。点击“重新AI拆解”生成阶段。
              </div>
            </div>

            <footer class="mt-4 flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                class="rounded-lg border border-sky-300/40 bg-sky-500/10 px-3 py-2 text-sm text-sky-100 transition hover:bg-sky-500/20"
                @click="$emit('add-step')"
              >
                + 新增阶段
              </button>

              <div class="flex items-center gap-2">
                <button
                  type="button"
                  class="rounded-lg border border-slate-600/70 bg-slate-900/75 px-3 py-2 text-sm text-slate-200 transition hover:border-sky-300/45"
                  @click="$emit('close')"
                >
                  取消
                </button>
                <button
                  type="button"
                  class="rounded-lg border border-sky-300/45 bg-sky-500/15 px-3 py-2 text-sm font-semibold text-sky-100 transition hover:bg-sky-500/25 disabled:cursor-not-allowed disabled:opacity-55"
                  :disabled="!draftItems.length || isGenerating"
                  @click="$emit('confirm')"
                >
                  确认写入阶段
                </button>
              </div>
            </footer>
          </section>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>
