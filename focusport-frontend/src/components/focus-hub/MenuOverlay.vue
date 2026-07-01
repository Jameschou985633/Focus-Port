<script setup>
defineProps({
  open: {
    type: Boolean,
    default: false
  },
  items: {
    type: Array,
    default: () => []
  }
})

defineEmits(['close'])

const modules = [
  { id: 'tasks', title: '任务列表', desc: '今日任务与状态' },
  { id: 'settings', title: '设置', desc: '账号与偏好配置' },
  { id: 'stats', title: '数据统计', desc: '专注与成长趋势' },
  { id: 'planning', title: 'AI 规划', desc: '目标分解与下一步' },
  { id: 'shop', title: '商店 / 背包', desc: '资源与道具入口' },
  { id: 'leaderboard', title: '排行榜 / 成就', desc: '进度与荣誉面板' }
]
</script>

<template>
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
      class="fixed inset-0 z-[100] flex justify-end bg-slate-950/60 backdrop-blur-sm"
      @click.self="$emit('close')"
    >
      <transition
        enter-active-class="transition duration-250 ease-out"
        enter-from-class="translate-x-7 opacity-0"
        enter-to-class="translate-x-0 opacity-100"
        leave-active-class="transition duration-180 ease-out"
        leave-from-class="translate-x-0 opacity-100"
        leave-to-class="translate-x-7 opacity-0"
      >
        <aside
          v-if="open"
          class="h-full w-full max-w-[34rem] border-l border-sky-300/30 bg-slate-950/95 p-4 shadow-[-20px_0_32px_rgba(2,6,23,0.45)] md:p-5"
        >
          <header class="flex items-start justify-between gap-3 rounded-2xl border border-sky-300/25 bg-slate-900/75 p-3">
            <div>
              <p class="text-xs uppercase tracking-[0.13em] text-sky-200/80">System Menu</p>
              <h3 class="mt-1 text-lg font-semibold text-slate-100">Command Overlay</h3>
            </div>
            <button
              type="button"
              class="grid h-9 w-9 place-items-center rounded-xl border border-sky-300/30 bg-slate-800/80 text-slate-200 transition duration-200 ease-out hover:bg-sky-500/20"
              @click="$emit('close')"
            >
              ✕
            </button>
          </header>

          <section class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="item in items"
              :key="item.key"
              class="inline-flex min-h-8 items-center rounded-full border border-sky-300/30 bg-sky-500/10 px-3 text-xs text-sky-100"
            >
              {{ item.label }}
            </span>
          </section>

          <section class="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              v-for="item in modules"
              :key="item.id"
              type="button"
              class="rounded-2xl border border-sky-300/25 bg-gradient-to-br from-slate-900/85 to-blue-950/65 p-3 text-left transition duration-200 ease-out hover:-translate-y-0.5 hover:border-sky-200/50"
            >
              <p class="text-base font-semibold text-slate-100">{{ item.title }}</p>
              <p class="mt-1 text-xs text-sky-200/80">{{ item.desc }}</p>
            </button>
          </section>
        </aside>
      </transition>
    </div>
  </transition>
</template>
