<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { shopApi, inventoryApi, infrastructureApi, focusEnergyApi } from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('username') || 'guest')

const categories = ['tree', 'building', 'decoration']
const activeCategory = ref('tree')

const items = ref([])
const inventory = ref([])
const placedItems = ref([])
const isLoading = ref(false)
const purchasingId = ref(null)
const userEnergy = ref(0)

const filteredItems = computed(() => {
  return items.value.filter(item => item.type === activeCategory.value)
})

// 检查物品是否已在背包中
const isInInventory = (itemId) => {
  return inventory.value.some(i => i.item_id === itemId)
}

// 加载用户专注能量
const loadUserEnergy = async () => {
  try {
    const res = await focusEnergyApi.get(username.value)
    userEnergy.value = res.data.focus_energy || 0
  } catch (error) {
    console.error('加载能量失败:', error)
    userEnergy.value = 0
  }
}

const loadShop = async () => {
  isLoading.value = true
  try {
    const res = await shopApi.items()
    items.value = res.data.items || []

    await loadInventory()
    await loadPlacedItems()
  } catch (error) {
    console.error('加载商店失败:', error)
  } finally {
    isLoading.value = false
  }
}

const loadInventory = async () => {
  try {
    const res = await inventoryApi.get(username.value)
    inventory.value = res.data.items || []
  } catch (error) {
    console.error('加载背包失败:', error)
    inventory.value = []
  }
}

const loadPlacedItems = async () => {
  try {
    const res = await infrastructureApi.get(username.value)
    placedItems.value = res.data.items || []
  } catch (error) {
    console.error('加载已放置物品失败:', error)
    placedItems.value = []
  }
}

const buyItem = async (item) => {
  if (purchasingId.value) return
  if (userEnergy.value < item.price) {
    alert(`专注能量不足！需要 ${item.price} 能量，当前 ${userEnergy.value} 能量`)
    return
  }
  if (!confirm(`确定要花费 ${item.price} 能量购买 ${item.name} 吗？`)) return

  purchasingId.value = item.id
  try {
    const res = await shopApi.buy(username.value, item.id)
    alert(res.data.message || '购买成功！')
    await loadUserEnergy()
    await loadInventory()
  } catch (error) {
    alert('购买失败: ' + (error.response?.data?.detail || '未知错误'))
  } finally {
    purchasingId.value = null
  }
}

const getRarityColor = (rarity) => {
  const colors = {
    common: '#9ca3af',
    rare: '#3b82f6',
    epic: '#a855f7',
    legendary: '#f59e0b'
  }
  return colors[rarity] || colors.common
}

const getRarityLabel = (rarity) => {
  const labels = {
    common: '普通',
    rare: '稀有',
    epic: '史诗',
    legendary: '传说'
  }
  return labels[rarity] || rarity
}
const goBack = () => router.push('/')

onMounted(() => {
  loadUserEnergy()
  loadShop()
  loadInventory()
  loadPlacedItems()
})
</script>

<template>
  <div class="shop-container">
    <div class="shop-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>🏪 建造商店</h1>
      <div class="user-energy">
        <span>🔋</span>
        <span>{{ userEnergy }}</span>
      </div>
    </div>

    <div class="shop-tabs">
      <button
        v-for="cat in categories"
        :key="cat"
        :class="['tab-btn', { active: activeCategory === cat }]"
        @click="activeCategory = cat"
      >
        {{ cat === 'tree' ? '🌲' : cat === 'building' ? '🏗️' : '🎯' }}
      </button>
    </div>

    <div class="shop-items">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="shop-item card-glass"
        :class="{ disabled: userEnergy < item.price, owned: isInInventory(item.id) }"
      >
        <div class="card-rarity" :style="{ background: getRarityColor(item.rarity) }">
          {{ getRarityLabel(item.rarity) }}
        </div>
        <div class="card-icon">{{ item.icon }}</div>
        <div class="card-info">
          <div class="card-name">{{ item.name }}</div>
          <div class="card-desc">{{ item.description || item.type }}</div>
        </div>
        <button
          v-if="isInInventory(item.id)"
          class="buy-btn owned"
          disabled
        >
          <span>✅</span>
          <span>已拥有</span>
        </button>
        <button
          v-else
          class="buy-btn"
          :class="{ disabled: userEnergy < item.price, loading: purchasingId === item.id }"
          :disabled="userEnergy < item.price || purchasingId === item.id"
          @click="buyItem(item)"
        >
          <span v-if="purchasingId === item.id" class="spinner-small"></span>
          <span v-else>💰</span>
          <span>{{ item.price }}</span>
        </button>
      </div>

      <div v-if="items.length === 0 && !isLoading" class="empty-state">
        <span class="empty-icon">🏪</span>
        <p>商店正在补货中...</p>
      </div>
    </div>

    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.shop-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
  color: white;
  padding-bottom: 100px;
}

.shop-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  margin-bottom: 16px;
}

.back-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

h1 {
  margin: 0;
  font-size: 24px;
}

.user-energy {
  background: rgba(251, 191, 36, 0.2);
  border: 1px solid rgba(251, 191, 36, 0.4);
  padding: 10px 20px;
  border-radius: 14px;
  font-weight: 600;
  font-size: 16px;
}

.shop-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tab-btn {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 14px;
  border-radius: 14px;
  cursor: pointer;
  font-size: 15px;
  transition: all 0.2s;
}

.tab-btn.active {
  background: rgba(74, 222, 128, 0.25);
  border-color: rgba(74, 222, 128, 0.5);
}

.shop-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.shop-item {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 20px 16px;
  text-align: center;
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s;
}

.shop-item:hover:not(.disabled) {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
}

.shop-item.disabled {
  opacity: 0.6;
}

.shop-item.owned {
  background: rgba(74, 222, 128, 0.15);
  border-color: rgba(74, 222, 128, 0.3);
}

.card-rarity {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 4px 10px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  color: white;
            text-transform: uppercase;
        }

.card-icon {
  font-size: 48px;
            margin-bottom: 12px;
        }

.card-info {
  margin-bottom: 16px;
  min-height: 50px;
        }
.card-name {
  font-size: 15px;
            font-weight: 600;
            margin-bottom: 4px;
        }
.card-desc {
  font-size: 12px;
            color: rgba(255, 255, 255, 0.6);
            line-height: 1.4;
        }

.buy-btn {
  width: 100%;
            background: rgba(251, 191, 36, 0.25);
            border: 1px solid rgba(251, 191, 36, 0.4);
            color: white;
            padding: 10px 12px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.2s;
        }
.buy-btn:hover:not(:disabled) {
  background: rgba(251, 191, 36, 0.4);
  transform: scale(1.02);
        }
.buy-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
        }
.buy-btn.owned {
  background: rgba(74, 222, 128, 0.25);
  border-color: rgba(74, 222, 128, 0.4);
        }
.buy-btn.loading {
  pointer-events: none;
        }
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
            padding: 60px 20px;
        }
.empty-icon {
            font-size: 48px;
            display: block;
            margin-bottom: 12px;
        }
.empty-state p {
            color: rgba(255, 255, 255, 0.5);
            margin: 0;
        }
.loading-overlay {
  position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
.spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-top-color: #4ade80;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 增加小图标动画 */
.shop-item {
  animation: bounce 0.3s ease;
}

@keyframes bounce {
  0% { transform: scale(0.9); }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); }
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>
