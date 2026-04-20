<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import RealIsland3D from './RealIsland3D.vue'
import IsometricCity from './IsometricCity.vue'
import DimensionBackpack from './DimensionBackpack.vue'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'

const route = useRoute()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()

const isPhysical = computed(() => dimensionStore.activeDimension === 'PHYSICAL')

const currentUsername = () => {
  if (typeof window === 'undefined') return 'guest'
  return window.localStorage.getItem('username') || 'guest'
}

const applyRouteDimension = (username = currentUsername()) => {
  const raw = Array.isArray(route.query.dimension)
    ? route.query.dimension[0]
    : route.query.dimension
  if (!raw) return false
  dimensionStore.setDimension(raw, username)
  return true
}

onMounted(async () => {
  const username = currentUsername()
  if (!applyRouteDimension(username)) {
    dimensionStore.rehydrate(username)
  }
  await inventoryStore.bootstrap()
  inventoryStore.consumeLegacyPendingPlacement()
})

watch(
  () => route.query.dimension,
  () => {
    applyRouteDimension(currentUsername())
  }
)
</script>

<template>
  <div class="dimension-shell">
    <div v-if="isPhysical" class="dimension-shell-physical">
      <RealIsland3D />
    </div>

    <div v-else class="dimension-shell-gaia">
      <!-- Skyline atmosphere (parallel to 3D) -->
      <div class="gaia-skyline-overlay">
        <div class="gaia-horizon"></div>
        <div class="gaia-orbital-ring gaia-orbital-a"></div>
        <div class="gaia-orbital-ring gaia-orbital-b"></div>
        <div class="gaia-city-haze"></div>
      </div>

      <IsometricCity />

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
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 18%, rgba(109, 92, 255, 0.25), transparent 24%),
    radial-gradient(circle at 50% 34%, rgba(76, 222, 255, 0.18), transparent 30%),
    linear-gradient(180deg, #02050e 0%, #050914 42%, #0a1122 72%, #08101e 100%);
  color: #eef7ff;
}

/* Skyline atmosphere — mirrors 3D */
.gaia-skyline-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.gaia-horizon {
  position: absolute;
  left: 50%;
  bottom: 20%;
  width: min(80vw, 920px);
  height: 240px;
  transform: translateX(-50%);
  background:
    linear-gradient(180deg, rgba(79, 115, 255, 0.02), rgba(79, 115, 255, 0.14)),
    repeating-linear-gradient(
      90deg,
      rgba(125, 177, 255, 0.12) 0,
      rgba(125, 177, 255, 0.12) 14px,
      transparent 14px,
      transparent 34px
    );
  clip-path: polygon(0 100%, 2% 64%, 6% 64%, 6% 42%, 11% 42%, 11% 78%, 16% 78%, 16% 30%, 22% 30%, 22% 70%, 29% 70%, 29% 24%, 36% 24%, 36% 84%, 41% 84%, 41% 44%, 48% 44%, 48% 18%, 54% 18%, 54% 74%, 62% 74%, 62% 36%, 69% 36%, 69% 62%, 76% 62%, 76% 26%, 83% 26%, 83% 72%, 90% 72%, 90% 54%, 95% 54%, 95% 100%);
  filter: drop-shadow(0 0 36px rgba(109, 92, 255, 0.3));
}

.gaia-orbital-ring {
  position: absolute;
  border-radius: 999px;
  border: 1px solid rgba(115, 224, 255, 0.16);
}

.gaia-orbital-a {
  width: 620px;
  height: 620px;
  top: -230px;
  left: 50%;
  transform: translateX(-50%);
}

.gaia-orbital-b {
  width: 760px;
  height: 760px;
  top: -300px;
  left: 50%;
  transform: translateX(-50%) rotate(18deg);
  border-color: rgba(109, 92, 255, 0.16);
}

.gaia-city-haze {
  position: absolute;
  left: 50%;
  bottom: 16%;
  width: min(90vw, 1040px);
  height: 220px;
  transform: translateX(-50%);
  background: radial-gradient(circle, rgba(76, 222, 255, 0.16), transparent 64%);
  filter: blur(26px);
}

.dimension-shell-physical {
  position: relative;
}
</style>
