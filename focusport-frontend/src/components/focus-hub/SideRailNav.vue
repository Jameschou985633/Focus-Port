<script setup>
defineProps({
  items: {
    type: Array,
    default: () => ([
      { key: 'core', label: 'Core', short: 'C' },
      { key: 'world', label: 'World', short: 'W' },
      { key: 'ai', label: 'AI', short: 'AI' },
      { key: 'social', label: 'Social', short: 'S' },
      { key: 'growth', label: 'Growth', short: 'G' },
      { key: 'economy', label: 'Economy', short: 'E' },
      { key: 'playground', label: 'Playground', short: 'P' },
      { key: 'system', label: 'System', short: 'SYS' }
    ])
  }
})
</script>

<template>
  <aside class="fixed inset-y-0 left-0 z-40 hidden w-[5.5rem] border-r border-sky-300/20 bg-slate-950/70 backdrop-blur md:flex md:flex-col" aria-label="Primary Navigation">
    <div class="mx-auto mt-3 flex h-11 w-11 items-center justify-center rounded-xl border border-sky-300/35 bg-sky-500/20 text-sm font-bold tracking-wide text-sky-100">
      FP
    </div>

    <nav class="mt-3 grid content-start gap-2 px-2">
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        class="grid min-h-[3.5rem] place-items-center rounded-2xl border border-sky-300/20 bg-slate-900/55 text-[10px] text-sky-100/80 transition duration-200 ease-out hover:-translate-y-0.5 hover:border-sky-200/45 hover:bg-sky-500/15 hover:text-sky-50"
        :title="item.label"
      >
        <span class="text-[11px] font-semibold tracking-wide">{{ item.short }}</span>
        <span class="text-[9px] uppercase tracking-[0.08em] text-slate-300/80">{{ item.label }}</span>
      </button>
    </nav>
  </aside>
</template>
