<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { aiApi } from '../../api'
import { WORLD_NAMES, composeWorldLabel } from '../../constants/worldNames'

const props = defineProps({
  username: { type: String, required: true },
  systemFeed: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['message-complete'])

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const quickPrompts = [
  '帮我安排今晚 90 分钟学习节奏',
  '根据最近状态给我一句提分建议',
  '我容易分心，给我一份 25 分钟执行清单'
]

const messages = ref([])
const inputText = ref('')
const isLoading = ref(false)
const messageListRef = ref(null)
const systemStatus = ref('')
const typingTimeouts = new Map()
let messageId = 1

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const clearTypingTimer = (id) => {
  const timer = typingTimeouts.get(id)
  if (timer) {
    clearTimeout(timer)
    typingTimeouts.delete(id)
  }
}

const finishMessage = async (entry) => {
  entry.displayedContent = entry.content
  entry.isTyping = false
  clearTypingTimer(entry.id)
  await scrollToBottom()
  emit('message-complete', {
    id: entry.id,
    channel: entry.channel,
    severity: entry.severity
  })
}

const typeMessage = async (entry, speed = 18) => {
  clearTypingTimer(entry.id)
  entry.displayedContent = ''
  entry.isTyping = true

  const step = async () => {
    const nextLength = entry.displayedContent.length + 1
    entry.displayedContent = entry.content.slice(0, nextLength)
    await scrollToBottom()
    if (nextLength >= entry.content.length) {
      await finishMessage(entry)
      return
    }
    const timer = setTimeout(step, speed)
    typingTimeouts.set(entry.id, timer)
  }

  const initial = setTimeout(step, speed)
  typingTimeouts.set(entry.id, initial)
}

const createMessage = ({
  role,
  content,
  channel = 'chat',
  severity = 'info',
  typewriter = false
}) => {
  const entry = {
    id: messageId++,
    role,
    content: String(content || ''),
    displayedContent: typewriter ? '' : String(content || ''),
    channel,
    severity,
    isTyping: false
  }
  messages.value.push(entry)
  return entry
}

const addTerminalMessage = async ({
  role = 'assistant',
  content = '',
  channel = 'chat',
  severity = 'info',
  typewriter = false
}) => {
  const entry = createMessage({ role, content, channel, severity, typewriter })
  await scrollToBottom()
  if (typewriter && entry.content) {
    await typeMessage(entry, channel === 'system' ? 20 : 16)
  } else {
    emit('message-complete', {
      id: entry.id,
      channel: entry.channel,
      severity: entry.severity
    })
  }
}

const loadHistory = async () => {
  try {
    const res = await aiApi.history(props.username)
    const history = res.data.messages || res.data.history || []
    messages.value = history.slice(-12).map((message) => ({
      id: messageId++,
      role: message.role,
      content: message.content || '',
      displayedContent: message.content || '',
      channel: 'chat',
      severity: 'info',
      isTyping: false
    }))
    await scrollToBottom()
  } catch (error) {
    messages.value = []
  }
}

const sendMessage = async (preset = '') => {
  const content = (preset || inputText.value).trim()
  if (!content || isLoading.value) return

  await addTerminalMessage({
    role: 'user',
    content,
    channel: 'chat',
    severity: 'info'
  })
  inputText.value = ''
  isLoading.value = true
  await scrollToBottom()

  try {
    const res = await aiApi.chat(props.username, content)
    const reply = res.data.reply || res.data.response || '舰载参谋端暂时没有返回内容。'
    await addTerminalMessage({
      role: 'assistant',
      content: reply,
      channel: 'chat',
      severity: 'success',
      typewriter: true
    })
  } catch (error) {
    await addTerminalMessage({
      role: 'assistant',
      content: '舰载参谋端暂时离线，请稍后再试。',
      channel: 'chat',
      severity: 'warning',
      typewriter: true
    })
  } finally {
    isLoading.value = false
    await scrollToBottom()
  }
}

const clearHistory = async () => {
  if (isLoading.value) return
  try {
    await axios.delete(`${API_BASE}/api/ai/history/${props.username}`)
    messages.value = []
  } catch (error) {
    await addTerminalMessage({
      role: 'assistant',
      content: '历史记录清理失败，请稍后重试。',
      channel: 'chat',
      severity: 'warning',
      typewriter: true
    })
  }
}

watch(
  () => props.systemFeed?.id,
  async (id) => {
    if (!id || !props.systemFeed) return
    const feed = props.systemFeed
    if (feed.status === 'pending') {
      systemStatus.value = feed.content || '[量子算力评估中...]'
      await scrollToBottom()
      return
    }

    systemStatus.value = ''
    await addTerminalMessage({
      role: 'assistant',
      content: feed.content || '',
      channel: feed.channel || 'system',
      severity: feed.severity || 'success',
      typewriter: true
    })
  }
)

onMounted(() => {
  loadHistory()
})

onBeforeUnmount(() => {
  Array.from(typingTimeouts.keys()).forEach((id) => clearTypingTimer(id))
})
</script>

<template>
  <div class="assistant-dock">
    <div class="assistant-toolbar">
      <span class="toolbar-title">{{ WORLD_NAMES.tacticalAdjutant.en }}</span>
      <button class="clear-btn" type="button" @click="clearHistory" :disabled="isLoading">CLEAR</button>
    </div>

    <div ref="messageListRef" class="message-list">
      <div v-if="messages.length === 0 && !systemStatus" class="empty-state">
        <span class="prompt-tag">SYS</span>
        <div>
          <strong>{{ composeWorldLabel(WORLD_NAMES.tacticalAdjutant) }}</strong>
          <p>副官在线，指挥官，请提交您的算力运行日志进行结算。</p>
        </div>
      </div>

      <div
        v-for="message in messages"
        :key="message.id"
        class="terminal-line"
        :class="[message.role, message.severity, message.channel]"
      >
        <span class="line-prefix">
          {{ message.role === 'user' ? 'CMD>' : message.channel === 'system' ? 'SYS>' : 'AI>' }}
        </span>
        <div class="line-body">
          <span>{{ message.displayedContent }}</span>
          <span v-if="message.isTyping" class="cursor">_</span>
        </div>
      </div>

      <div v-if="systemStatus" class="terminal-line assistant pending system">
        <span class="line-prefix">SYS&gt;</span>
        <div class="line-body">
          <span>{{ systemStatus }}</span>
          <span class="cursor">_</span>
        </div>
      </div>

      <div v-if="isLoading" class="terminal-line assistant info chat">
        <span class="line-prefix">AI&gt;</span>
        <div class="line-body">
          <span>正在整理建议...</span>
          <span class="cursor">_</span>
        </div>
      </div>
    </div>

    <div v-if="messages.length === 0" class="quick-prompts">
      <button
        v-for="prompt in quickPrompts"
        :key="prompt"
        type="button"
        class="prompt-btn"
        @click="sendMessage(prompt)"
      >
        {{ prompt }}
      </button>
    </div>

    <div class="input-row">
      <span class="line-prefix fixed">CMD&gt;</span>
      <input
        v-model="inputText"
        type="text"
        placeholder="输入你当前需要的学习建议"
        :disabled="isLoading"
        @keyup.enter="sendMessage()"
      />
      <button type="button" class="send-btn" :disabled="!inputText.trim() || isLoading" @click="sendMessage()">
        SEND
      </button>
    </div>
  </div>
</template>

<style scoped>
.assistant-dock {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 420px;
  color: #baf9ff;
}

.assistant-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-title {
  font-family: 'Consolas', 'SFMono-Regular', monospace;
  font-size: 12px;
  letter-spacing: 0.18em;
  color: rgba(123, 249, 255, 0.82);
}

.clear-btn,
.send-btn,
.prompt-btn {
  border: 1px solid rgba(96, 238, 255, 0.22);
  background: rgba(8, 22, 30, 0.94);
  color: #cfffff;
  cursor: pointer;
}

.clear-btn {
  border-radius: 10px;
  padding: 8px 12px;
}

.message-list {
  flex: 1;
  min-height: 260px;
  max-height: 360px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(1, 10, 14, 0.96), rgba(1, 18, 24, 0.96)),
    rgba(0, 0, 0, 0.9);
  border: 1px solid rgba(86, 246, 255, 0.18);
  box-shadow: inset 0 0 0 1px rgba(66, 215, 255, 0.06);
}

.empty-state {
  display: flex;
  gap: 10px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(8, 28, 36, 0.72);
  border: 1px solid rgba(96, 238, 255, 0.14);
}

.empty-state p {
  margin: 6px 0 0;
  color: rgba(186, 249, 255, 0.72);
  font-size: 12px;
}

.prompt-tag,
.line-prefix {
  flex: none;
  min-width: 44px;
  font-family: 'Consolas', 'SFMono-Regular', monospace;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.terminal-line {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-family: 'Consolas', 'SFMono-Regular', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.terminal-line .line-body {
  flex: 1;
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.terminal-line.user .line-prefix {
  color: #8bf8ff;
}

.terminal-line.assistant.chat .line-prefix {
  color: #7ee0ff;
}

.terminal-line.system .line-prefix {
  color: #ffd66d;
}

.terminal-line.warning .line-prefix,
.terminal-line.warning .line-body {
  color: #ff8d8d;
}

.terminal-line.success .line-body {
  color: #c6fff2;
}

.terminal-line.pending .line-body {
  color: #ffe08a;
}

.cursor {
  display: inline-block;
  margin-left: 2px;
  animation: blink 0.9s steps(1) infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.quick-prompts {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.prompt-btn {
  border-radius: 12px;
  padding: 10px 12px;
  text-align: left;
}

.input-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
  border-radius: 16px;
  padding: 10px 12px;
  background: rgba(1, 10, 14, 0.94);
  border: 1px solid rgba(96, 238, 255, 0.18);
}

.input-row input {
  width: 100%;
  min-width: 0;
  border: none;
  background: transparent;
  color: #d5ffff;
  font-family: 'Consolas', 'SFMono-Regular', monospace;
  outline: none;
}

.input-row input::placeholder {
  color: rgba(186, 249, 255, 0.42);
}

.send-btn {
  border-radius: 10px;
  padding: 8px 14px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.send-btn:disabled,
.clear-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fixed {
  align-self: center;
}
</style>
