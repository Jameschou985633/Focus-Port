<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const props = defineProps({
  username: { type: String, required: true }
})

const emit = defineEmits(['item-used'])

const items = ref([])
const showInventory = ref(false)
const selectedItem = ref(null)
const isLoading = ref(false)

const rarityColors = {
  common: '#9ca3af',
  rare: '#3b82f6',
  epic: '#a855f7',
  legendary: '#f59e0b'
}

const rarityLabels = {
  common: '普通',
  rare: '稀有',
  epic: '史诗',
  legendary: '传说'
}

const totalItems = computed(() => {
  return items.value.reduce((sum, item) => sum + item.quantity, 0)
})

const loadInventory = async () => {
  isLoading.value = true
  try {
    const res = await axios.get(`http://127.0.0.1:8000/api/items/inventory/${props.username}`)
    items.value = res.data.items
  } catch (error) {
    console.error('加载背包失败:', error)
  } finally {
    isLoading.value = false
  }
}

const selectItem = (item) => {
  selectedItem.value = item
}

const useItem = async () => {
  if (!selectedItem.value) return

  try {
    await axios.post('http://127.0.0.1:8000/api/items/use', {
      username: props.username,
      item_id: selectedItem.value.item_id
    })

    emit('item-used', selectedItem.value)
    selectedItem.value = null
    loadInventory()
  } catch (error) {
    console.error('使用道具失败:', error)
    alert('使用失败，请稍后重试')
  }
}

onMounted(loadInventory)

defineExpose({ loadInventory })
</script>

<template>
  <div class="inventory-container">
    <!-- 背包按钮 -->
    <button class="inventory-toggle" @click="showInventory = !showInventory">
      <span class="icon">🎁</span>
      <span class="label">背包</span>
      <span v-if="totalItems > 0" class="badge">{{ totalItems }}</span>
    </button>

    <!-- 背包面板 -->
    <div v-if="showInventory" class="inventory-panel">
      <div class="panel-header">
        <h3>🎁 我的道具</h3>
        <button class="refresh-btn" @click="loadInventory" :disabled="isLoading">
          {{ isLoading ? '...' : '🔄' }}
        </button>
      </div>

      <!-- 道具网格 -->
      <div class="items-grid">
        <div
          v-for="item in items"
          :key="item.item_id"
          class="item-card"
          :style="{ borderColor: rarityColors[item.rarity] }"
          @click="selectItem(item)"
        >
          <div class="item-icon">🎁</div>
          <div class="item-name">{{ item.name }}</div>
          <div class="item-qty">x{{ item.quantity }}</div>
          <div
            class="rarity-tag"
            :style="{ background: rarityColors[item.rarity] }"
          >
            {{ rarityLabels[item.rarity] }}
          </div>
        </div>

        <div v-if="items.length === 0" class="empty-hint">
          <p>🎒 背包空空如也</p>
          <p class="hint">完成任务获取道具吧！</p>
        </div>
      </div>

      <!-- 道具详情弹窗 -->
      <div v-if="selectedItem" class="item-detail-overlay" @click.self="selectedItem = null">
        <div class="item-detail-modal">
          <h4 :style="{ color: rarityColors[selectedItem.rarity] }">
            {{ selectedItem.name }}
          </h4>
          <p class="rarity-badge" :style="{ background: rarityColors[selectedItem.rarity] }">
            {{ rarityLabels[selectedItem.rarity] }}
          </p>
          <p class="desc">{{ selectedItem.description }}</p>
          <p class="effect">效果: {{ selectedItem.effect_type }}</p>
          <div class="modal-actions">
            <button class="use-btn" @click="useItem">使用</button>
            <button class="close-btn" @click="selectedItem = null">关闭</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 🌟 毛玻璃容器 */
.inventory-container {
  position: relative;
  pointer-events: auto !important;
  z-index: 999;
}

/* 🌟 毛玻璃按钮 */
.inventory-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(30, 40, 60, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 2px solid rgba(255, 200, 100, 0.5);
  border-radius: 16px;
  color: white;
  padding: 14px 22px;
  cursor: pointer !important;
  font-size: 15px;
  font-weight: 600;
  transition: all 0.3s ease;
  text-shadow: 0px 1px 3px rgba(0, 0, 0, 0.3);
  pointer-events: auto !important;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  position: relative;
}

.inventory-toggle:hover {
  background: rgba(50, 70, 100, 0.9);
  border-color: rgba(255, 220, 100, 0.8);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
}

.badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: linear-gradient(135deg, #f87171, #ef4444);
  color: white;
  font-size: 11px;
  font-weight: bold;
  padding: 2px 7px;
  border-radius: 12px;
  min-width: 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.4);
}

/* 🌟 毛玻璃面板 - 向左展开 */
.inventory-panel {
  position: absolute;
  right: auto;
  left: -380px;
  top: 0;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 24px;
  padding: 20px;
  width: 360px;
  max-height: 450px;
  overflow-y: auto;
  z-index: 10000;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  color: white;
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
}

.refresh-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 10px;
  transition: all 0.3s;
}

.refresh-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.item-card {
  background: rgba(255, 255, 255, 0.15);
  border: 2px solid;
  border-radius: 16px;
  padding: 12px 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.item-card:hover {
  transform: translateY(-4px) scale(1.02);
  background: rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.item-icon {
  font-size: 28px;
  margin-bottom: 6px;
}

.item-name {
  color: white;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.1);
}

.item-qty {
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
}

.rarity-tag {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 8px;
  color: white;
  font-weight: 600;
}

.empty-hint {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px 0;
  color: white;
}

.empty-hint p {
  margin: 6px 0;
  text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.1);
}

.hint {
  font-size: 12px;
  opacity: 0.7;
}

/* 🌟 道具详情弹窗 - 毛玻璃风格 */
.item-detail-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
}

.item-detail-modal {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 28px;
  padding: 28px;
  width: 300px;
  text-align: center;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15);
}

.item-detail-modal h4 {
  margin: 0 0 14px 0;
  font-size: 22px;
  text-shadow: 0px 2px 4px rgba(0, 0, 0, 0.1);
}

.rarity-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
  color: white;
  margin-bottom: 16px;
}

.desc {
  color: white;
  font-size: 14px;
  margin: 10px 0;
  line-height: 1.6;
  text-shadow: 0px 1px 2px rgba(0, 0, 0, 0.1);
}

.effect {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  margin-bottom: 20px;
}

.modal-actions {
  display: flex;
  gap: 12px;
}

.use-btn {
  flex: 1;
  background: rgba(74, 222, 128, 0.3);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(74, 222, 128, 0.5);
  color: white;
  padding: 12px;
  border-radius: 50px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
}

.use-btn:hover {
  background: rgba(74, 222, 128, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(74, 222, 128, 0.3);
}

.close-btn {
  flex: 1;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 12px;
  border-radius: 50px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}
</style>
