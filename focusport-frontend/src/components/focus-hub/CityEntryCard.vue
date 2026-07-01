<script setup>
defineEmits(['enter-3d', 'enter-2d'])
</script>

<template>
  <section class="rounded-2xl border border-sky-300/20 bg-slate-950/45 p-4 backdrop-blur-md">
    <p class="text-lg font-semibold text-slate-200">City Presence</p>
    <div class="mt-4 grid gap-2">
      <button
        type="button"
        class="min-h-11 rounded-xl border border-sky-300/30 bg-gradient-to-r from-slate-800/80 to-blue-900/55 text-sm font-semibold text-slate-100 transition duration-200 ease-out hover:-translate-y-0.5 hover:border-sky-200/55"
        @click="$emit('enter-3d')"
      >
        Enter 3D City
      </button>
      <button
        type="button"
        class="min-h-11 rounded-xl border border-sky-300/30 bg-gradient-to-r from-slate-800/80 to-blue-900/55 text-sm font-semibold text-slate-100 transition duration-200 ease-out hover:-translate-y-0.5 hover:border-sky-200/55"
        @click="$emit('enter-2d')"
      >
        Enter 2D City
      </button>
    </div>
  </section>
</template>
