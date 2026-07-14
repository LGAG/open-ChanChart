<script setup>
import { useTheme } from './composables/useTheme'
import Home from './views/Home.vue'
import AppHeader from './components/AppHeader.vue'
import AppBackground from './components/AppBackground.vue'

// initialize theme system (applies stored theme on first call)
const { isDark } = useTheme()
</script>

<template>
  <div id="app">
    <AppBackground v-if="isDark" />
    <AppHeader />
    <main class="app-main">
      <Home />
    </main>
  </div>
</template>

<style>
#app {
  min-height: 100vh;
  background: var(--bg);
}

.app-main {
  padding-top: 48px;
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
</style>