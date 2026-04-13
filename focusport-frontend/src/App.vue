<script setup>
import BackgroundMusic from './components/BackgroundMusic.vue'
import DimensionTransitionOverlay from './components/DimensionTransitionOverlay.vue'
</script>

<template>
  <router-view />
  <DimensionTransitionOverlay />
  <BackgroundMusic />
</template>

<style>
/* 清除浏览器默认的内外边距，防止出现水平滚动条 */
html, body {
  margin: 0;
  padding: 0;
  overflow-x: hidden;
  overflow-y: auto !important;
  min-height: 100%;
}

#app {
  width: 100%;
  min-height: 100%;
  overflow-y: auto;
}
</style>
