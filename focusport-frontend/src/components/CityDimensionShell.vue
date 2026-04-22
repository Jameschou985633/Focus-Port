<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RealIsland3D from './RealIsland3D.vue'
import IsometricCity from './IsometricCity.vue'
import DimensionBackpack from './DimensionBackpack.vue'
import { useDimensionStore } from '../stores/dimension'
import { useInventoryStore } from '../stores/inventory'

const route = useRoute()
const router = useRouter()
const dimensionStore = useDimensionStore()
const inventoryStore = useInventoryStore()

const isPhysical = computed(() => dimensionStore.activeDimension === 'PHYSICAL')
const worldTitle = computed(() => (isPhysical.value ? '物理世界' : '盖亚拓扑'))
const worldMode = computed(() => (isPhysical.value ? '3D' : '2D'))

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

const switchDimension = (dimension) => {
  dimensionStore.setDimension(dimension, currentUsername())
}

const openShop = () => {
  router.push('/shop')
}

const openBackpack = () => {
  window.dispatchEvent(new CustomEvent('blueprint-vault-open'))
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
    <header class="world-hud">
      <div class="world-title">
        <span>{{ worldMode }} MAP</span>
        <strong>{{ worldTitle }}</strong>
        <small>购买建筑，打开背包，然后在当前地图建造。</small>
      </div>

      <nav class="world-switch" aria-label="地图维度切换">
        <button
          type="button"
          :class="{ active: isPhysical }"
          @click="switchDimension('PHYSICAL')"
        >
          3D 物理世界
        </button>
        <button
          type="button"
          :class="{ active: !isPhysical }"
          @click="switchDimension('GAIA')"
        >
          2D 盖亚拓扑
        </button>
      </nav>

      <div class="world-actions">
        <button type="button" class="ghost" @click="openBackpack">打开背包</button>
        <button type="button" class="primary" @click="openShop">购买建筑</button>
      </div>
    </header>

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

.world-hud {
  position: fixed;
  top: 18px;
  left: 50%;
  z-index: 42;
  width: min(980px, calc(100vw - 36px));
  min-height: 64px;
  transform: translateX(-50%);
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto auto;
  align-items: center;
  gap: 14px;
  padding: 12px 14px 12px 18px;
  border-radius: 24px;
  border: 1px solid rgba(115, 224, 255, 0.2);
  background:
    radial-gradient(circle at 20% 0%, rgba(72, 128, 255, 0.18), transparent 36%),
    rgba(7, 16, 34, 0.72);
  color: #eef7ff;
  box-shadow: 0 20px 54px rgba(3, 8, 22, 0.34);
  backdrop-filter: blur(18px);
}

.world-title {
  display: grid;
  gap: 2px;
}

.world-title span {
  color: rgba(156, 230, 255, 0.8);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.16em;
}

.world-title strong {
  font-size: 18px;
  line-height: 1.1;
}

.world-title small {
  color: rgba(238, 247, 255, 0.66);
  font-size: 12px;
}

.world-switch,
.world-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.world-switch {
  padding: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
}

.world-hud button {
  border: 0;
  min-height: 38px;
  border-radius: 999px;
  padding: 0 14px;
  color: rgba(238, 247, 255, 0.76);
  background: transparent;
  font-weight: 800;
  cursor: pointer;
}

.world-switch button.active {
  color: #fff;
  background: linear-gradient(135deg, #4880ff, #6d5cff);
  box-shadow: 0 10px 24px rgba(72, 128, 255, 0.28);
}

.world-actions .ghost {
  background: rgba(255, 255, 255, 0.08);
}

.world-actions .primary {
  color: #fff;
  background: #4880ff;
}

@media (max-width: 820px) {
  .world-hud {
    top: 10px;
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .world-switch,
  .world-actions {
    justify-content: stretch;
  }

  .world-switch button,
  .world-actions button {
    flex: 1;
  }
}
</style>
