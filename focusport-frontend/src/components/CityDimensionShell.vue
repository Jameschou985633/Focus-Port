<script setup>
import { computed, onMounted } from 'vue'
import RealIsland3D from './RealIsland3D.vue'
import IsometricCity from './IsometricCity.vue'
import ThreeDPreviewDock from './ThreeDPreviewDock.vue'
import DimensionBackpack from './DimensionBackpack.vue'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'
import { WORLD_NAMES, composeWorldLabel } from '../constants/worldNames'

const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()

const isPhysical = computed(() => dimensionStore.activeDimension === 'PHYSICAL')

const switchToGaia = () => dimensionStore.playDimensionTransition('GAIA')
const switchToPhysical = () => dimensionStore.playDimensionTransition('PHYSICAL')

onMounted(async () => {
  dimensionStore.rehydrate()
  await inventoryStore.bootstrap()
  inventoryStore.consumeLegacyPendingPlacement()
})
</script>

<template>
  <div class="dimension-shell">
    <div v-if="isPhysical" class="dimension-shell-physical">
      <RealIsland3D />
      <button type="button" class="dimension-return" @click="switchToGaia">
        {{ composeWorldLabel(WORLD_NAMES.gaia) }}
      </button>
    </div>

    <div v-else class="dimension-shell-gaia">
      <IsometricCity />
      <div v-if="dimensionStore.preview3DVisible" class="preview-dock-wrap">
        <ThreeDPreviewDock :title="composeWorldLabel(WORLD_NAMES.physical)" @activate="switchToPhysical" />
      </div>
    </div>

    <DimensionBackpack />
  </div>
</template>

<style scoped>
.dimension-shell,
.dimension-shell-gaia,
.dimension-shell-physical {
  min-height: 100vh;
}

.dimension-shell-gaia {
  position: relative;
  background:
    radial-gradient(circle at 20% 18%, rgba(47, 216, 255, 0.14), transparent 20%),
    radial-gradient(circle at 78% 14%, rgba(109, 92, 255, 0.18), transparent 22%),
    #0a192f;
}

.preview-dock-wrap {
  position: fixed;
  left: 16px;
  bottom: 18px;
  z-index: 24;
}

.dimension-shell-physical {
  position: relative;
}

.dimension-return {
  position: fixed;
  top: 16px;
  right: 18px;
  z-index: 16;
  min-height: 42px;
  border: 1px solid rgba(115, 224, 255, 0.28);
  border-radius: 999px;
  padding: 0 18px;
  background: rgba(7, 16, 34, 0.84);
  color: #eef7ff;
  cursor: pointer;
  backdrop-filter: blur(10px);
}

@media (max-width: 768px) {
  .preview-dock-wrap {
    left: 12px;
    right: 12px;
    bottom: 14px;
  }

  .dimension-return {
    right: 14px;
    top: 12px;
    max-width: calc(100vw - 28px);
    font-size: 12px;
  }
}
</style>
