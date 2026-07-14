// Theme registry — single source of truth for all themes.
// To add a new theme: push one object into the `themes` array. Nothing else
// needs to change — the switcher, CSS vars, and ECharts palette all derive
// from this array. See useTheme.js for how `vars`/`echarts` are applied.
//
// `vars`    → CSS custom properties set on :root (consumed via var(--...) in any CSS)
// `echarts` → KlineChart color palette (consumed by the chart option builder)
// `dark`    → whether to load Element Plus dark css-vars, show animated bg, add html.dark

// Variables shared by every theme (so var(--...) resolves in all modes):
//   --bg --panel-bg --panel-border --accent --accent2 --text --text-dim --grid-line --glow --font

export const themes = [
  {
    key: 'classic',
    label: '经典',
    mode: 'light',
    dark: false,
    swatch: '#409eff',
    vars: {
      '--bg': '#f5f5f5',
      '--panel-bg': '#ffffff',
      '--panel-border': '#ebeef5',
      '--accent': '#409eff',
      '--accent2': '#67c23a',
      '--text': '#303133',
      '--text-dim': '#909399',
      '--grid-line': 'rgba(0, 0, 0, 0.06)',
      '--glow': 'none',
      '--font': "system-ui, Avenir, Helvetica, Arial, sans-serif"
    },
    echarts: {
      grid: '#ffffff',
      axis: '#909399',
      text: '#303133',
      up: '#ef232a',
      down: '#14b143',
      pen: '#0000FF',
      seg: '#FF6600',
      zsh: 'rgba(255, 0, 0, 0.3)',
      zsl: 'rgba(0, 255, 0, 0.3)',
      split: '#eee',
      bg: '#ffffff'
    }
  },
  {
    key: 'cyberpunk',
    label: '赛博朋克',
    mode: 'dark',
    dark: true,
    swatch: '#ff2d95',
    vars: {
      '--bg': '#0a0014',
      '--panel-bg': 'rgba(20, 8, 40, 0.55)',
      '--panel-border': 'rgba(255, 45, 155, 0.4)',
      '--accent': '#ff2d95',
      '--accent2': '#00d0ff',
      '--text': '#ffe0f0',
      '--text-dim': '#b97ad0',
      '--grid-line': 'rgba(255, 45, 155, 0.09)',
      '--glow': '0 0 20px rgba(255, 45, 155, 0.5)',
      '--font': "'Courier New', 'Consolas', monospace"
    },
    echarts: {
      grid: '#3a1a4d',
      axis: '#b14dff',
      text: '#ff7ae0',
      up: '#ff2d6b',
      down: '#00ff9d',
      pen: '#00d0ff',
      seg: '#ffae00',
      zsh: 'rgba(255, 45, 155, 0.4)',
      zsl: 'rgba(0, 255, 157, 0.4)',
      split: 'rgba(255, 45, 155, 0.08)',
      bg: 'transparent'
    }
  },
  {
    key: 'hologram',
    label: '全息投影',
    mode: 'dark',
    dark: true,
    swatch: '#2dffd5',
    vars: {
      '--bg': '#02141a',
      '--panel-bg': 'rgba(8, 40, 48, 0.45)',
      '--panel-border': 'rgba(45, 255, 213, 0.4)',
      '--accent': '#2dffd5',
      '--accent2': '#00a2ff',
      '--text': '#c8fff5',
      '--text-dim': '#5fbfae',
      '--grid-line': 'rgba(45, 255, 213, 0.08)',
      '--glow': '0 0 20px rgba(45, 255, 213, 0.45)',
      '--font': "'Courier New', 'Consolas', monospace"
    },
    echarts: {
      grid: '#0a3d3d',
      axis: '#2dffd5',
      text: '#a8fff0',
      up: '#ff4d6b',
      down: '#2dffd5',
      pen: '#00e5ff',
      seg: '#ffe14d',
      zsh: 'rgba(45, 255, 213, 0.35)',
      zsl: 'rgba(0, 180, 255, 0.35)',
      split: 'rgba(45, 255, 213, 0.08)',
      bg: 'transparent'
    }
  },
  {
    key: 'deepspace',
    label: '深空科技',
    mode: 'dark',
    dark: true,
    swatch: '#4d8bff',
    vars: {
      '--bg': '#02061a',
      '--panel-bg': 'rgba(8, 16, 48, 0.55)',
      '--panel-border': 'rgba(77, 139, 255, 0.4)',
      '--accent': '#4d8bff',
      '--accent2': '#6deeff',
      '--text': '#c8d6ff',
      '--text-dim': '#6a7fb5',
      '--grid-line': 'rgba(77, 139, 255, 0.08)',
      '--glow': '0 0 24px rgba(77, 139, 255, 0.4)',
      '--font': "'Courier New', 'Consolas', monospace"
    },
    echarts: {
      grid: '#0a1a3d',
      axis: '#4d8bff',
      text: '#9db8ff',
      up: '#ff4d6b',
      down: '#4dffa6',
      pen: '#6da4ff',
      seg: '#ffd24d',
      zsh: 'rgba(77, 139, 255, 0.3)',
      zsl: 'rgba(120, 200, 255, 0.3)',
      split: 'rgba(77, 139, 255, 0.08)',
      bg: 'transparent'
    }
  },
  {
    key: 'mecha',
    label: '机甲HUD',
    mode: 'dark',
    dark: true,
    swatch: '#ffae00',
    vars: {
      '--bg': '#0d0a02',
      '--panel-bg': 'rgba(40, 28, 6, 0.6)',
      '--panel-border': 'rgba(255, 174, 0, 0.5)',
      '--accent': '#ffae00',
      '--accent2': '#00d8ff',
      '--text': '#ffe9b8',
      '--text-dim': '#b8975a',
      '--grid-line': 'rgba(255, 174, 0, 0.1)',
      '--glow': '0 0 18px rgba(255, 174, 0, 0.45)',
      '--font': "'Courier New', 'Consolas', monospace"
    },
    echarts: {
      grid: '#3a2a0a',
      axis: '#ffae00',
      text: '#ffd97a',
      up: '#ff3b3b',
      down: '#7aff4d',
      pen: '#00d8ff',
      seg: '#ffae00',
      zsh: 'rgba(255, 174, 0, 0.35)',
      zsl: 'rgba(0, 216, 255, 0.35)',
      split: 'rgba(255, 174, 0, 0.1)',
      bg: 'transparent'
    }
  }
]

export const defaultTheme = 'classic'

export const storageKey = 'chanchart-theme'
