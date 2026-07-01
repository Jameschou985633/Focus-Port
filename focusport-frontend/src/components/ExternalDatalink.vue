<script setup>
import { ref } from 'vue'

const isExpanded = ref(false)

const links = [
  {
    id: 'audio-decrypt',
    name: '声学解码频段 · AUDIO DECRYPTION',
    tag: '// 欧路词典听力源',
    url: 'https://dict.eudic.net/ting'
  },
  {
    id: 'earth-brief',
    name: '地球观测简报 · EARTH DAILY BRIEF',
    tag: '// China Daily 文本情报',
    url: 'https://www.chinadaily.com.cn/'
  },
  {
    id: 'bili-archive',
    name: '影像档案 · BILI VISUAL ARCHIVE',
    tag: '// 哔哩哔哩学习视窗',
    url: 'https://space.bilibili.com/1035929235'
  }
]

const toggleExpanded = () => {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <section class="datalink-panel" :class="{ expanded: isExpanded }">
    <button
      type="button"
      class="panel-toggle"
      :aria-expanded="isExpanded ? 'true' : 'false'"
      @click="toggleExpanded"
    >
      <span class="toggle-copy">
        <span class="header-icon">◉</span>
        <span class="header-title">外接数据链路 · EXTERNAL DATALINK</span>
      </span>
      <span class="toggle-arrow" :class="{ expanded: isExpanded }">⌄</span>
    </button>

    <div class="panel-body" :class="{ expanded: isExpanded }">
      <div class="link-list">
        <a
          v-for="link in links"
          :key="link.id"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          class="datalink-item"
        >
          <span class="signal-dot"></span>
          <div class="link-content">
            <span class="link-name">{{ link.name }}</span>
            <span class="link-tag">{{ link.tag }}</span>
          </div>
          <span class="link-arrow">↗</span>
        </a>
      </div>
    </div>
  </section>
</template>

<style scoped>
.datalink-panel {
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(115, 224, 255, 0.15);
  overflow: hidden;
}

.panel-toggle {
  width: 100%;
  border: none;
  background: transparent;
  color: inherit;
  padding: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  text-align: left;
}

.panel-toggle:hover {
  background: rgba(255, 255, 255, 0.04);
}

.toggle-copy {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  color: #4ade80;
  animation: pulse 2s infinite;
  flex: 0 0 auto;
}

.header-title {
  min-width: 0;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(156, 223, 255, 0.72);
  font-weight: 600;
}

.toggle-arrow {
  flex: 0 0 auto;
  color: rgba(156, 223, 255, 0.62);
  font-size: 14px;
  transition: transform 0.22s ease, color 0.22s ease;
}

.toggle-arrow.expanded {
  transform: rotate(180deg);
  color: #73e0ff;
}

.panel-body {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.24s ease;
}

.panel-body.expanded {
  grid-template-rows: 1fr;
}

.link-list {
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 14px 0;
}

.panel-body.expanded .link-list {
  max-height: 220px;
  overflow-y: auto;
  padding: 0 14px 14px;
  scrollbar-color: #00ffff rgba(10, 25, 47, 0.9);
  scrollbar-width: thin;
}

.panel-body.expanded .link-list::-webkit-scrollbar {
  width: 6px;
}

.panel-body.expanded .link-list::-webkit-scrollbar-track {
  background: rgba(10, 25, 47, 0.9);
  border-radius: 999px;
}

.panel-body.expanded .link-list::-webkit-scrollbar-thumb {
  background: #00ffff;
  border-radius: 999px;
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.45);
}

.datalink-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(115, 224, 255, 0.1);
  border-radius: 10px;
  text-decoration: none;
  cursor: crosshair;
  transition: all 0.2s ease;
  overflow: hidden;
}

.datalink-item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(74, 222, 128, 0.05), transparent);
  transform: translateX(-100%);
  transition: transform 0.4s ease;
}

.datalink-item:hover::before {
  transform: translateX(100%);
}

.datalink-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(74, 222, 128, 0.4);
  box-shadow: 0 0 20px rgba(74, 222, 128, 0.15);
}

.signal-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  transition: all 0.2s ease;
}

.datalink-item:hover .signal-dot {
  background: #4ade80;
  box-shadow: 0 0 8px #4ade80, 0 0 16px rgba(74, 222, 128, 0.5);
  animation: blink 0.6s infinite;
}

.link-content {
  flex: 1;
  min-width: 0;
}

.link-name {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #eef7ff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: text-shadow 0.2s ease;
}

.datalink-item:hover .link-name {
  text-shadow: 0 0 8px rgba(238, 247, 255, 0.6);
  animation: glitch 0.15s ease;
}

.link-tag {
  display: block;
  font-size: 10px;
  color: rgba(222, 240, 255, 0.5);
  margin-top: 2px;
  font-family: 'Roboto Mono', 'Consolas', monospace;
}

.link-arrow {
  font-size: 14px;
  color: rgba(222, 240, 255, 0.3);
  transition: all 0.2s ease;
}

.datalink-item:hover .link-arrow {
  color: #4ade80;
  transform: translateX(4px);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.4;
  }
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.3;
  }
}

@keyframes glitch {
  0% {
    transform: translateX(0);
  }

  25% {
    transform: translateX(-1px);
  }

  50% {
    transform: translateX(1px);
  }

  75% {
    transform: translateX(-0.5px);
  }

  100% {
    transform: translateX(0);
  }
}
</style>
