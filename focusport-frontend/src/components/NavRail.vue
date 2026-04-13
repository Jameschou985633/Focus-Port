<script setup>
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const props = defineProps({
  activeId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select'])

const navItems = [
  {
    id: 'adjutant',
    icon: 'AI',
    label: composeWorldLabel(WORLD_NAMES.tacticalAdjutant),
    subtitle: WORLD_NAMES.tacticalAdjutant.en
  },
  {
    id: 'exchange',
    icon: 'EX',
    label: composeWorldLabel(WORLD_NAMES.exchangePort),
    subtitle: WORLD_NAMES.exchangePort.en
  },
  {
    id: 'vault',
    icon: 'BP',
    label: composeWorldLabel(WORLD_NAMES.blueprintVault),
    subtitle: WORLD_NAMES.blueprintVault.en
  },
  {
    id: 'fleet',
    icon: 'FX',
    label: composeWorldLabel(WORLD_NAMES.fleetNexus),
    subtitle: WORLD_NAMES.fleetNexus.en
  },
  {
    id: 'protocol',
    icon: 'PR',
    label: composeWorldLabel(WORLD_NAMES.protocolStation),
    subtitle: WORLD_NAMES.protocolStation.en
  }
]
</script>

<template>
  <aside class="nav-rail">
    <button
      v-for="item in navItems"
      :key="item.id"
      type="button"
      class="nav-rail-btn"
      :class="{ active: props.activeId === item.id }"
      :data-blueprint-vault-anchor="item.id === 'vault' ? 'true' : null"
      @click="emit('select', item.id)"
    >
      <span class="rail-icon">{{ item.icon }}</span>
      <span class="rail-copy">
        <strong>{{ item.label }}</strong>
        <small>{{ item.subtitle }}</small>
      </span>
    </button>
  </aside>
</template>

<style scoped>
.nav-rail {
  position: absolute;
  right: 22px;
  top: 96px;
  z-index: 9;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nav-rail-btn {
  width: 192px;
  min-height: 64px;
  border: 1px solid rgba(0, 255, 255, 0.18);
  border-radius: 18px;
  padding: 10px 12px;
  background:
    linear-gradient(180deg, rgba(10, 26, 46, 0.96), rgba(6, 13, 30, 0.98)),
    rgba(4, 9, 20, 0.92);
  color: #eefcff;
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 12px;
  align-items: center;
  cursor: pointer;
  box-shadow: 0 18px 34px rgba(3, 8, 22, 0.34);
}

.nav-rail-btn.active {
  border-color: rgba(0, 255, 255, 0.4);
  box-shadow: 0 0 0 1px rgba(0, 255, 255, 0.14), 0 18px 34px rgba(3, 8, 22, 0.34);
}

.rail-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: rgba(0, 255, 255, 0.08);
  color: #9ef8ff;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.rail-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
}

.rail-copy strong {
  font-size: 12px;
  line-height: 1.4;
  text-shadow: 0 0 14px rgba(0, 255, 255, 0.16);
}

.rail-copy small {
  font-family: 'Roboto Mono', 'Consolas', monospace;
  font-size: 10px;
  letter-spacing: 0.1em;
  color: rgba(158, 248, 255, 0.68);
}

@media (max-width: 768px) {
  .nav-rail {
    display: none;
  }
}
</style>
