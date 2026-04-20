<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { aiApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const messages = ref([])
const inputText = ref('')
const isLoading = ref(false)
const messagesContainer = ref(null)

const quickQuestions = [
  { icon: '🎯', text: '分析我的薄弱点' },
  { icon: '📚', text: '推荐学习计划' },
  { icon: '💡', text: '如何提高专注力?' },
  { icon: '🔥', text: '怎样保持学习动力?' }
]

const loadHistory = async () => {
  try {
    const res = await aiApi.history(userStore.username)
    messages.value = res.data.messages || res.data.history || []
    scrollToBottom()
  } catch (error) {
    console.error('加载对话历史失败:', error)
  }
}

const sendMessage = async (text = null) => {
  const messageText = text || inputText.value.trim()
  if (!messageText || isLoading.value) return

  const userMessage = { role: 'user', content: messageText }
  messages.value.push(userMessage)
  inputText.value = ''
  isLoading.value = true
  scrollToBottom()

  try {
    const res = await aiApi.chat(userStore.username, messageText)
    messages.value.push({
      role: 'assistant',
      content: res.data.reply || res.data.response
    })
    scrollToBottom()
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，我遇到了一些问题，请稍后再试。'
    })
  } finally {
    isLoading.value = false
  }
}

const clearHistory = async () => {
  if (!confirm('确定要清空所有对话记录吗？')) return

  try {
    await aiApi.clearHistory(userStore.username)
    messages.value = []
  } catch (error) {
    console.error('清空失败:', error)
    alert('清空失败，请稍后重试')
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const goBack = () => router.push('/')

onMounted(() => loadHistory())
</script>

<template>
  <div class="ai-container">
    <div class="ai-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>🤖 副官终端</h1>
      <button class="clear-btn" @click="clearHistory" :disabled="messages.length === 0">
        🗑️ 清空
      </button>
    </div>

    <div class="chat-area">
      <!-- 消息列表 - 可滚动 -->
      <div class="messages" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">🎓</div>
          <h2>你好，{{ userStore.username }}！</h2>
          <p>我是你的副官终端，可以帮助你：</p>
          <ul>
            <li>🎯 分析学习薄弱点</li>
            <li>📚 制定个性化学习计划</li>
            <li>💡 提供学习方法和技巧</li>
            <li>🔥 激励你保持学习动力</li>
          </ul>
        </div>

        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.role]"
        >
          <div class="message-avatar">
            {{ msg.role === 'user' ? '👤' : '🤖' }}
          </div>
          <div class="message-content">{{ msg.content }}</div>
        </div>

        <div v-if="isLoading" class="message assistant">
          <div class="message-avatar">🤖</div>
          <div class="message-content loading">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
      </div>

      <!-- 快捷问题 -->
      <div class="quick-questions" v-if="messages.length === 0">
        <button
          v-for="(q, i) in quickQuestions"
          :key="i"
          class="quick-btn"
          @click="sendMessage(q.text)"
        >
          {{ q.icon }} {{ q.text }}
        </button>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <input
          v-model="inputText"
          type="text"
          placeholder="输入你的问题..."
          @keyup.enter="sendMessage()"
          :disabled="isLoading"
        />
        <button class="send-btn" @click="sendMessage()" :disabled="isLoading || !inputText.trim()">
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-container {
  height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  display: flex;
  flex-direction: column;
  color: white;
  overflow: hidden;
}

.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
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

h1 { margin: 0; font-size: 24px; }

.clear-btn {
  background: rgba(248, 113, 113, 0.2);
  border: 1px solid rgba(248, 113, 113, 0.3);
  color: rgba(255, 255, 255, 0.8);
  padding: 8px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.clear-btn:hover:not(:disabled) {
  background: rgba(248, 113, 113, 0.35);
}

.clear-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
  min-height: 0;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  margin-bottom: 12px;
  min-height: 0;

  /* 自定义滚动条 */
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
}

.messages::-webkit-scrollbar {
  width: 6px;
}

.messages::-webkit-scrollbar-track {
  background: transparent;
}

.messages::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

.welcome {
  text-align: center;
  padding: 40px 20px;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.welcome h2 {
  margin: 0 0 12px 0;
  font-size: 24px;
}

.welcome p {
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 16px;
}

.welcome ul {
  list-style: none;
  padding: 0;
  text-align: left;
  display: inline-block;
}

.welcome li {
  padding: 8px 0;
  font-size: 15px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.message-content {
  max-width: 75%;
  padding: 14px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.1);
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.message.user .message-content {
  background: rgba(74, 222, 128, 0.25);
  border: 1px solid rgba(74, 222, 128, 0.3);
}

.message.assistant .message-content {
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.message-content.loading {
  display: flex;
  gap: 6px;
  padding: 16px 24px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  animation: bounce 1.4s infinite ease-in-out;
}

.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1.2); opacity: 1; }
}

.quick-questions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.quick-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: white;
  padding: 10px 16px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.quick-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.input-area {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.input-area input {
  flex: 1;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 14px;
  color: white;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
}

.input-area input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.input-area input:focus {
  border-color: rgba(74, 222, 128, 0.5);
}

.send-btn {
  padding: 14px 28px;
  background: rgba(74, 222, 128, 0.25);
  border: 1px solid rgba(74, 222, 128, 0.4);
  color: white;
  border-radius: 14px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: rgba(74, 222, 128, 0.4);
  transform: translateY(-2px);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 响应式设计 - 平板 */
@media (max-width: 1023px) {
  .ai-header {
    padding: 14px 20px;
  }

  .chat-area {
    padding: 12px;
    max-width: 100%;
  }

  .messages {
    padding: 12px;
  }

  .welcome {
    padding: 30px 16px;
  }

  .welcome-icon {
    font-size: 48px;
  }

  .welcome h2 {
    font-size: 20px;
  }
}

/* 响应式设计 - 移动端 */
@media (max-width: 767px) {
  .ai-container {
    padding-bottom: calc(var(--mobile-nav-height, 64px) + env(safe-area-inset-bottom, 0));
  }

  .ai-header {
    padding: 12px 16px;
  }

  .back-btn {
    padding: 8px 14px;
    font-size: 13px;
  }

  h1 {
    font-size: 18px;
  }

  .clear-btn {
    padding: 6px 12px;
    font-size: 12px;
  }

  .chat-area {
    padding: 10px;
  }

  .messages {
    padding: 10px;
    border-radius: 16px;
    margin-bottom: 10px;
  }

  .welcome {
    padding: 24px 12px;
  }

  .welcome-icon {
    font-size: 40px;
    margin-bottom: 12px;
  }

  .welcome h2 {
    font-size: 18px;
  }

  .welcome p {
    font-size: 14px;
  }

  .welcome li {
    font-size: 13px;
    padding: 6px 0;
  }

  .message {
    gap: 10px;
    margin-bottom: 12px;
  }

  .message-avatar {
    width: 32px;
    height: 32px;
    font-size: 16px;
  }

  .message-content {
    max-width: 85%;
    padding: 12px 14px;
    font-size: 14px;
  }

  .quick-questions {
    gap: 6px;
  }

  .quick-btn {
    padding: 8px 12px;
    font-size: 12px;
    border-radius: 10px;
  }

  .input-area {
    gap: 10px;
  }

  .input-area input {
    padding: 12px 14px;
    font-size: 14px;
    border-radius: 12px;
  }

  .send-btn {
    padding: 12px 20px;
    font-size: 14px;
    border-radius: 12px;
  }
}
</style>
