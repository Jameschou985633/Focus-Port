<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { shopApi, inventoryApi, islandApi } from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('username') || 'guest')

// 用户数据
const userDiamonds = ref(0)
const userEnergy = ref(0)
const userSkins = ref([])
const inventory = ref([])

// 商店数据
const decorations = ref([])
const boosts = ref([])
const skins = ref([])

// UI状态
const isLoading = ref(false)
const activeTab = ref('decorations')
const purchasingId = ref(null)

// 加载用户钻石
const loadUserDiamonds = async () => {
  try {
    const res = await shopApi.diamonds(username.value)
    userDiamonds.value = res.data.diamonds || 0
  } catch (error) {
    console.error('加载钻石失败:', error)
    userDiamonds.value = 0
  }
}

// 加载商店物品
const loadShop = async () => {
  isLoading.value = true
  try {
    // 加载装饰物和皮肤
    const [decorRes, skinsRes] = await Promise.all([
      shopApi.studyroomItems(),
      islandApi.skins()
    ])
    decorations.value = decorRes.data.items || []
    skins.value = skinsRes.data.skins || []

    // 加载用户数据
    await Promise.all([loadInventory(), loadUserSkins()])
  } catch (error) {
    console.error('加载商店失败:', error)
  } finally {
    isLoading.value = false
  }
}

// 加载背包
const loadInventory = async () => {
  try {
    const res = await inventoryApi.get(username.value)
    inventory.value = res.data.items || []
  } catch (error) {
    console.error('加载背包失败:', error)
    inventory.value = []
  }
}

// 加载用户皮肤
const loadUserSkins = async () => {
  try {
    const res = await islandApi.userSkins(username.value)
    userSkins.value = res.data.owned_skins || []
  } catch (error) {
    console.error('加载用户皮肤失败:', error)
    userSkins.value = []
  }
}

// 检查是否在背包中
const isInInventory = (itemId) => {
  return inventory.value.some(i => i.item_id === itemId)
}

// 检查是否拥有皮肤
const isSkinOwned = (skinId) => {
  return userSkins.value.includes(skinId)
}

// 购买装饰
const buyDecoration = async (item) => {
  if (purchasingId.value) return
  if (userDiamonds.value < item.price) {
    alert(`钻石不足！需要 ${item.price} 鄿石 当前 ${userDiamonds.value}`)
    return
  }
  if (!confirm(`确定要花费 ${item.price} 鑫石购买 ${item.name} 吗?`)) return

  purchasingId.value = item.id
  try {
    const res = await shopApi.buyStudyroom(username.value, item.id)
    alert(res.data.message || '购买成功!')
    await loadUserDiamonds()
    await loadInventory()
  } catch (error) {
    alert('购买失败: ' + (error.response?.data?.detail || '未知错误'))
  } finally {
    purchasingId.value = null
  }
}

// 购买皮肤
const buySkin = async (skin) => {
  if (purchasingId.value) return
  if (isSkinOwned(skin.id)) {
    alert('你已经拥有这个皮肤了！')
    return
  }
  if (userDiamonds.value < skin.cost) {
    alert(`钻石不足!需要 ${skin.cost} 鑫石 当前 ${userDiamonds.value}`)
    return
  }
  if (!confirm(`确定要花费 ${skin.cost} 鑫石购买 ${skin.name} 吗?`)) return
  purchasingId.value = skin.id
  try {
    const res = await islandApi.buySkin(username.value, skin.id)
    alert(res.data.message || '购买成功!')
    await loadUserDiamonds()
    await loadUserSkins()
  } catch (error) {
    alert('购买失败: ' + (error.response?.data?.detail || '未知错误'))
  } finally {
    purchasingId.value = null
  }
}

// 购买功能道具
const buyBoost = async (item) => {
  if (purchasingId.value) return
  if (userDiamonds.value < item.price) {
    alert(`钻石不足!需要 ${item.price} 鑫石`)
    return
  }
  if (!confirm(`确定要花费 ${item.price} 鑫石购买 ${item.name}?\n效果: ${item.effect}\n时长: ${item.duration}分钟`)) return

  purchasingId.value = item.id
  try {
    const res = await shopApi.buyStudyroom(username.value, item.id)
    alert(res.data.message || '购买成功!')
    await loadUserDiamonds()
    await loadInventory()
  } catch (error) {
    alert('购买失败: ' + (error.response?.data?.detail || '未知错误'))
  } finally {
    purchasingId.value = null
  }
}

onMounted(() => {
  loadShop()
})

const goBack = () => router.push('/')
</script>

<template>
  <div class="shop-container">
    <!-- 顶部导航 -->
    <div class="shop-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>🏪 线上自习室商店</h1>
      <div class="currency-display">
        <span class="currency-icon">💎</span>
        <span class="currency-amount">{{ userDiamonds }}</span>
      </div>
    </div>

    <!-- 分类Tab -->
    <div class="tabs">
      <button :class="['tab', { active: activeTab === 'decorations' }]" @click="activeTab = 'decorations'">装饰</button>
      <button :class="['tab', { active: activeTab === 'boosts' }]" @click="activeTab = 'boosts'">道具</button>
      <button :class="['tab', { active: activeTab === 'skins' }]" @click="activeTab = 'skins'">皮肤</button>
    </div>

    <!-- 商品列表 -->
    <div class="shop-content">
      <!-- 装饰分类 -->
      <div v-if="activeTab === 'decorations'" class="items-grid">
        <div v-for="item in decorations" :key="item.id" class="shop-card"
          :class="{ owned: isInInventory(item.id), 'rare': item.rarity === 'legendary' }">
          <div class="card-icon">{{ item.icon }}</div>
          <div class="card-name">{{ item.name }}</div>
          <div class="card-price">
            <span class="price-diamond">💎 {{ item.price }}</span>
          </div>
          <button
            v-if="!isInInventory(item.id)"
            class="buy-btn"
            :disabled="purchasingId === item.id || userDiamonds < item.price"
            @click="buyDecoration(item)"
          >
            {{ purchasingId === item.id ? '购买中...' : '购买' }}
          </button>
        </div>
      </div>

      <!-- 功能道具 -->
      <div v-if="activeTab === 'boosts'" class="items-grid">
        <div v-for="item in boosts" :key="item.id" class="shop-card" :class="item.rarity">
          <div class="card-icon">{{ item.icon }}</div>
          <div class="card-name">{{ item.name }}</div>
          <div class="card-effect">{{ item.effect }}</div>
          <div class="card-price">
            <span class="price-diamond">💎 {{ item.price }}</span>
          </div>
          <button
            class="buy-btn"
            :disabled="purchasingId === item.id || userDiamonds < item.price"
            @click="buyBoost(item)"
          >
            {{ purchasingId === item.id ? '购买中...' : '购买' }}
          </button>
        </div>
      </div>

      <!-- 皮肤 -->
      <div v-if="activeTab === 'skins'" class="items-grid">
        <div v-for="skin in skins" :key="skin.id" class="shop-card" :class="{ owned: isSkinOwned(skin.id) }">
          <div class="card-icon">{{ skin.icon }}</div>
          <div class="card-name">{{ skin.name }}</div>
          <div class="card-price">
            <span class="price-diamond">💎 {{ skin.cost }}</span>
          </div>
          <button
            v-if="!isSkinOwned(skin.id)"
            class="buy-btn"
            :disabled="purchasingId === skin.id || userDiamonds < skin.cost"
            @click="buySkin(skin)"
          >
            {{ purchasingId === skin.id ? '购买中...' : '购买' }}
          </button>
          <span v-else class="owned-label">已拥有</span>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.shop-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 20px;
  color: white;
}

.shop-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
}

.back-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}
.back-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}
h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}
.currency-display {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(251, 191, 36, 0.2);
  padding: 8px 16px;
  border-radius: 20px;
}
.currency-icon {
  font-size: 20px;
}
.currency-amount {
  font-size: 18px;
  font-weight: 700;
  color: #fbbf24;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.tab {
  padding: 12px 24px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.2s;
}
.tab.active {
  background: rgba(251, 191, 36, 0.2);
  border-color: rgba(251, 191, 36, 0.4);
  color: white;
}
.shop-content {
  flex: 1;
}
.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}
.shop-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 16px;
  text-align: center;
  transition: all 0.2s;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.shop-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.2);
}
.shop-card.owned {
  border-color: rgba(74, 222, 128, 0.4);
  background: rgba(74, 222, 128, 0.1);
}
.shop-card.rare {
  border-color: rgba(59, 130, 246, 0.4);
}
.shop-card.epic {
  border-color: rgba(139, 92, 246, 0.4);
}
.shop-card.legendary {
  border-color: rgba(251, 191, 36, 0.5);
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(245, 158, 11, 0.2));
}
.card-icon {
  font-size: 48px;
  margin-bottom: 8px;
}
.card-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}
.card-effect {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 8px;
}
.card-price {
  margin-bottom: 12px;
}
.price-diamond {
  color: #fbbf24;
  font-weight: 600;
}
.buy-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.3), rgba(245, 158, 11, 0.3));
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.buy-btn:hover:not(:disabled) {
  transform: scale(1.02);
}
.buy-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.owned-label {
  display: inline-block;
  padding: 6px 12px;
  background: rgba(74, 222, 128, 0.2);
  border-radius: 12px;
  font-size: 12px;
  color: #4ade80;
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
  border-top-color: #fbbf24;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 嚗应式设计 - 移动端 */
@media (max-width: 767px) {
  .shop-container {
    padding: 12px;
    padding-bottom: calc(var(--mobile-nav-height, 64px) + 20px);
  }
  .shop-header {
    padding: 12px 16px;
  }
  h1 {
    font-size: 20px;
  }
  .items-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .shop-card {
    padding: 12px;
  }
  .card-icon {
    font-size: 36px;
  }
  .card-name {
    font-size: 14px;
  }
}
</style>
