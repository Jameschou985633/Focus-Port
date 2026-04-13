<script setup>
import { computed } from 'vue'
import { WORLD_NAMES, composeWorldLabel } from '../../constants/worldNames'

const props = defineProps({
  rooms: {
    type: Array,
    default: () => []
  }
})

const archiveEntries = computed(() => {
  if (!props.rooms.length) {
    return []
  }

  return props.rooms.slice(0, 6).map((room, index) => {
    const occupied = Number(room.current_users || 0)
    const capacity = Math.max(Number(room.max_seats || 1), 1)
    const progress = Math.min(100, Math.round((occupied / capacity) * 100))
    return {
      id: room.id || `${room.name || 'archive'}-${index}`,
      commander: room.owner_username || room.owner || room.name || `Commander ${index + 1}`,
      berth: occupied > 0 ? 'Docked In Current Ring' : 'Holding Pattern',
      progress,
      note: room.description || 'Fleet telemetry pending uplink.'
    }
  })
})
</script>

<template>
  <section class="archive-shell">
    <header class="archive-header">
      <div>
        <p class="archive-kicker">{{ WORLD_NAMES.starshipArchive.en }}</p>
        <h2>{{ composeWorldLabel(WORLD_NAMES.starshipArchive) }}</h2>
      </div>
      <span class="archive-chip">{{ archiveEntries.length }} SIGNALS</span>
    </header>

    <div v-if="archiveEntries.length" class="archive-grid">
      <article v-for="entry in archiveEntries" :key="entry.id" class="archive-card">
        <div class="archive-row">
          <strong>{{ entry.commander }}</strong>
          <span>{{ entry.berth }}</span>
        </div>
        <p>{{ entry.note }}</p>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${entry.progress}%` }"></div>
        </div>
        <small>Mission Progress {{ entry.progress }}%</small>
      </article>
    </div>

    <div v-else class="archive-empty">
      No fleet telemetry available yet. Publish a public dock to populate the archive.
    </div>
  </section>
</template>

<style scoped>
.archive-shell {
  border-radius: 24px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(10, 26, 46, 0.96), rgba(6, 13, 30, 0.98)),
    rgba(4, 9, 20, 0.92);
  border: 1px solid rgba(0, 255, 255, 0.16);
  box-shadow: 0 24px 56px rgba(2, 8, 18, 0.28);
}

.archive-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.archive-kicker {
  margin: 0 0 6px;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: rgba(164, 245, 255, 0.68);
}

.archive-header h2 {
  margin: 0;
  font-size: 20px;
  color: #eefcff;
  text-shadow: 0 0 16px rgba(0, 255, 255, 0.22);
}

.archive-chip {
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 700;
  color: #9ef8ff;
  background: rgba(0, 255, 255, 0.08);
  border: 1px solid rgba(0, 255, 255, 0.16);
}

.archive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.archive-card {
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(0, 255, 255, 0.08);
}

.archive-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  color: #eefcff;
}

.archive-row strong {
  font-size: 14px;
}

.archive-row span,
.archive-card small,
.archive-card p {
  color: rgba(214, 247, 255, 0.68);
}

.archive-card p {
  margin: 10px 0 12px;
  line-height: 1.5;
  min-height: 42px;
}

.progress-track {
  height: 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #00f5ff, #2684ff);
}

.archive-empty {
  margin-top: 16px;
  border-radius: 18px;
  padding: 18px;
  color: rgba(214, 247, 255, 0.62);
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed rgba(0, 255, 255, 0.14);
}
</style>
