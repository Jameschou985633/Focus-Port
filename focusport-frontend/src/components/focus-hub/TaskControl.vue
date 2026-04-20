<script setup>
defineProps({
  tasks: {
    type: Array,
    default: () => []
  },
  selectedTaskId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select-task'])

const onTaskChange = (event) => {
  emit('select-task', String(event.target.value || ''))
}
</script>

<template>
  <section class="rounded-2xl border border-sky-300/20 bg-slate-950/45 p-4 backdrop-blur-md">
    <p class="text-lg font-semibold text-slate-200">Current Task</p>

    <label class="mt-4 block text-xs uppercase tracking-[0.12em] text-sky-200/70" for="task-select">Task</label>
    <select
      id="task-select"
      class="mt-2 min-h-11 w-full rounded-xl border border-sky-300/25 bg-slate-900/70 px-3 text-sm text-slate-100 outline-none transition duration-200 ease-out focus:border-sky-300/55 focus:ring-2 focus:ring-sky-400/20"
      :value="selectedTaskId"
      @change="onTaskChange"
    >
      <option value="">Select task</option>
      <option v-for="task in tasks" :key="task.id" :value="task.id">{{ task.title }}</option>
    </select>
  </section>
</template>
