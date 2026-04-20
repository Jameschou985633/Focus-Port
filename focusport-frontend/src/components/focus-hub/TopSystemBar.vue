<script setup>
defineProps({
  username: {
    type: String,
    default: 'guest'
  }
})

defineEmits(['go-home', 'back-map', 'enter-city'])
</script>

<template>
  <header class="fixed left-3 right-3 top-3 z-50 flex min-h-16 items-center justify-between gap-3 rounded-2xl border border-sky-300/30 bg-slate-950/70 px-3 shadow-[0_16px_30px_rgba(2,6,23,0.45)] backdrop-blur-xl md:left-[6.25rem] md:right-6 md:px-4">
    <button type="button" class="min-w-0 text-left" @click="$emit('go-home')">
      <p class="hidden text-[10px] uppercase tracking-[0.14em] text-sky-200/75 md:block">FOCUSPORT / SELF-DISCIPLINE NEXUS</p>
      <p class="text-2xl font-semibold tracking-tight text-slate-100">FocusPort</p>
    </button>

    <div class="flex items-center gap-2">
      <span class="hidden rounded-xl border border-sky-300/25 bg-slate-900/65 px-2 py-1 text-xs text-slate-300 md:inline">{{ username }}</span>
      <button
        type="button"
        class="inline-flex min-h-10 items-center rounded-xl border border-sky-300/35 bg-slate-900/80 px-3 text-sm font-medium text-slate-100 transition duration-200 ease-out hover:-translate-y-0.5 hover:border-sky-200/55 hover:bg-sky-500/15"
        @click="$emit('back-map')"
      >
        Back to Map
      </button>
      <button
        type="button"
        class="inline-flex min-h-10 items-center rounded-xl border border-sky-300/50 bg-gradient-to-r from-blue-600 to-sky-500 px-3 text-sm font-semibold text-white transition duration-200 ease-out hover:-translate-y-0.5 hover:shadow-[0_12px_22px_rgba(37,99,235,0.35)]"
        @click="$emit('enter-city')"
      >
        Enter City
      </button>
    </div>
  </header>
</template>
