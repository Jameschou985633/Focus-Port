<script setup>
import GlobalSequencePanel from './GlobalSequencePanel.vue'
import MasterTimelineBoard from './MasterTimelineBoard.vue'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const emit = defineEmits(['draft-deployed', 'start-timeline-task'])
</script>

<template>
  <aside class="right-sidebar">
    <section class="sidebar-card todo-shell">
      <header class="card-header">
        <div>
          <p class="card-kicker">{{ WORLD_NAMES.globalSequence.en }}</p>
          <h2>{{ composeWorldLabel(WORLD_NAMES.globalSequence) }}</h2>
        </div>
      </header>

      <div class="todo-content">
        <GlobalSequencePanel @draft-deployed="emit('draft-deployed', $event)" />
        <MasterTimelineBoard @start-task="emit('start-timeline-task', $event)" />
      </div>
    </section>
  </aside>
</template>

<style scoped>
.right-sidebar {
  position: absolute;
  top: 78px;
  right: 22px;
  width: min(380px, calc(100vw - 44px));
  height: calc(100vh - 96px);
  min-height: 0;
  display: flex;
  flex-direction: column;
  z-index: 9;
  pointer-events: auto;
}

.todo-shell {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  border-radius: 24px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(16, 34, 74, 0.95), rgba(8, 16, 36, 0.96)),
    rgba(11, 18, 32, 0.86);
  border: 1.5px solid rgba(129, 214, 255, 0.34);
  box-shadow: 0 20px 54px rgba(4, 8, 22, 0.44);
  backdrop-filter: blur(18px);
  color: #eef7ff;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.card-kicker {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(156, 223, 255, 0.72);
}

.card-header h2 {
  margin: 0;
  font-size: 22px;
  text-shadow: 0 0 18px rgba(0, 255, 255, 0.16);
}

.todo-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: rgba(115, 224, 255, 0.4) rgba(10, 25, 47, 0.6);
}

.todo-content::-webkit-scrollbar {
  width: 6px;
}

.todo-content::-webkit-scrollbar-track {
  background: rgba(10, 25, 47, 0.6);
  border-radius: 999px;
}

.todo-content::-webkit-scrollbar-thumb {
  background: rgba(115, 224, 255, 0.4);
  border-radius: 999px;
}

.todo-content::-webkit-scrollbar-thumb:hover {
  background: rgba(115, 224, 255, 0.6);
}

@media (max-width: 768px) {
  .right-sidebar {
    top: 70px;
    right: 12px;
    width: calc(100vw - 24px);
    height: auto;
    max-height: calc(100vh - 156px);
  }
}
</style>
