<script setup>
import { ref } from 'vue'

const props = defineProps({
  recentAchievement: { type: Object, default: null },
  communityUpdates: { type: Array, default: () => [] }
})

const emit = defineEmits(['view-community', 'dismiss-achievement'])

// 婊氬姩娑堟伅
const messages = ref([
  '馃尡 瀹屾垚浠婃棩绗竴涓笓娉紝鑾峰緱鎴愰暱鍊?+10',
  '馃摎 绯荤粺鎻愮ず锛氭ā鎷熻€冭瘯鍔熻兘宸蹭笂绾?,
  '馃帀 鎭枩锛佷綘鑾峰緱浜嗐€屽垵绾ц嚜寰嬭€呫€嶅窘绔?
])

const currentMessageIndex = ref(0)

const nextMessage = () => {
  currentMessageIndex.value = (currentMessageIndex.value + 1) % messages.value.length
}
</script>

<template>
  <div class="bottom-info-bar">
    <!-- 婊氬姩娑堟伅 -->
    <div class="message-roller" @click="nextMessage">
      <span class="message-icon">馃挕</span>
      <span class="message-text">{{ messages[currentMessageIndex] }}</span>
      <span class="message-nav">鈼忊棌鈼?/span>
    </div>

    <!-- 蹇嵎鍏ュ彛 -->
    <div class="quick-actions">
      <button class="quick-btn" title="绀惧尯骞垮満">
        <span>馃彉锔?/span>
        <span class="btn-label">绀惧尯</span>
      </button>
      <button class="quick-btn" title="鎴愬氨澧?>
        <span>馃弳</span>
        <span class="btn-label">鎴愬氨</span>
      </button>
      <button class="quick-btn" title="鏁版嵁缁熻">
        <span>馃搳</span>
        <span class="btn-label">缁熻</span>
      </button>
    </div>

    <!-- 鐗堟潈淇℃伅 -->
    <div class="copyright">
      FocusPort 专注星港 · 学习使我快乐
    </div>
  </div>
</template>

<style scoped>
.bottom-info-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 48px;
  z-index: 999 !important;
  pointer-events: auto !important;

  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;

  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* 婊氬姩娑堟伅 */
.message-roller {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  cursor: pointer;
  transition: all 0.2s;
}

.message-roller:hover {
  background: rgba(255, 255, 255, 0.15);
}

.message-icon {
  font-size: 14px;
}

.message-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.message-nav {
  font-size: 8px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 2px;
}

/* 蹇嵎鍏ュ彛 */
.quick-actions {
  display: flex;
  gap: 8px;
}

.quick-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  color: white;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.btn-label {
  font-size: 12px;
  opacity: 0.8;
}

/* 鐗堟潈淇℃伅 */
.copyright {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

/* 鍝嶅簲寮忚璁?- 骞虫澘 */
@media (max-width: 1023px) {
  .bottom-info-bar {
    padding: 0 16px;
  }

  .message-text {
    max-width: 200px;
  }

  .quick-btn {
    padding: 6px 10px;
  }

  .btn-label {
    display: none;
  }
}

/* 鍝嶅簲寮忚璁?- 绉诲姩绔?*/
@media (max-width: 767px) {
  /* 绉诲姩绔殣钘忓簳閮ㄦ爮锛岀敤 MobileNav 鏇夸唬 */
  .bottom-info-bar {
    display: none;
  }
}
</style>


