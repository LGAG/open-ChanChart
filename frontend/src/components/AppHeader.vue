<template>
  <header class="app-header">
    <div class="brand">
      <span class="brand-mark">◆</span>
      <span class="brand-text">ChanChart <span class="brand-accent">缠论终端</span></span>
    </div>

    <div class="theme-switch">
      <span class="switch-label">主题</span>
      <el-select
        :model-value="currentTheme"
        @update:model-value="setTheme"
        size="small"
        class="theme-select"
      >
        <el-option
          v-for="t in themes"
          :key="t.key"
          :label="t.label"
          :value="t.key"
        >
          <div class="theme-option">
            <span class="swatch" :style="{ background: t.swatch, boxShadow: '0 0 6px ' + t.swatch }"></span>
            <span>{{ t.label }}</span>
          </div>
        </el-option>
      </el-select>
    </div>
  </header>
</template>

<script setup>
import { useTheme } from '../composables/useTheme'

const { currentTheme, themes, setTheme } = useTheme()
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--panel-bg);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--panel-border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--text);
  font-family: var(--font);
}

.brand-mark {
  color: var(--accent);
  text-shadow: var(--glow);
}

.brand-accent {
  color: var(--accent);
  font-size: 13px;
}

.theme-switch {
  display: flex;
  align-items: center;
  gap: 10px;
}

.switch-label {
  font-size: 13px;
  color: var(--text-dim);
  white-space: nowrap;
}

.theme-select {
  width: 140px;
}

.theme-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.swatch {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* keep the selected label readable on dark themes */
:deep(.theme-select .el-select__wrapper) {
  background: var(--panel-bg);
  box-shadow: 0 0 0 1px var(--panel-border) inset;
}
:deep(.theme-select .el-select__placeholder),
:deep(.theme-select .el-select__selected-item) {
  color: var(--text);
}
</style>
