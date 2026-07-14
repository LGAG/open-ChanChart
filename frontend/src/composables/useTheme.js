// Singleton theme composable — shared across the whole app (no Pinia needed).
// Module-level state means every caller of useTheme() sees the same refs.
//
// On theme change it:
//   1. sets <html data-theme="key">
//   2. toggles <html class="dark"> (Element Plus dark css-vars is keyed on html.dark)
//   3. loads/unloads EP dark css-vars via a runtime <link> (so it can be removed)
//   4. injects the theme's CSS custom properties onto :root
import { ref, computed } from 'vue'
import { themes, defaultTheme, storageKey } from './themes'

// Vite resolves this to a stable asset URL in both dev and prod.
import darkCssUrl from 'element-plus/theme-chalk/dark/css-vars.css?url'

const STORAGE_KEY = storageKey

function loadFromStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && themes.some(t => t.key === saved)) return saved
  } catch (e) {
    // localStorage may be unavailable (private mode) — fall back to default
  }
  return defaultTheme
}

// Module-level singleton state
const currentTheme = ref(loadFromStorage())
let darkLink = null      // the <link> element for EP dark css-vars, when loaded
let initialized = false  // apply() runs once on first useTheme() call

function apply(key) {
  const desc = themes.find(t => t.key === key)
  if (!desc) return

  const root = document.documentElement

  // 1. data-theme attr — drives our [data-theme="..."] CSS + AppBackground
  root.dataset.theme = key

  // 2. html.dark class — activates Element Plus dark css-vars
  root.classList.toggle('dark', desc.dark)

  // 3. EP dark css-vars link management (loadable + removable)
  if (desc.dark && !darkLink) {
    darkLink = document.createElement('link')
    darkLink.rel = 'stylesheet'
    darkLink.href = darkCssUrl
    darkLink.dataset.epDark = ''
    document.head.appendChild(darkLink)
  } else if (!desc.dark && darkLink) {
    darkLink.remove()
    darkLink = null
  }

  // 4. inject this theme's CSS vars onto :root (overwrites previous theme)
  for (const [prop, value] of Object.entries(desc.vars)) {
    root.style.setProperty(prop, value)
  }
}

function setTheme(key) {
  if (!themes.some(t => t.key === key)) return
  try {
    localStorage.setItem(STORAGE_KEY, key)
  } catch (e) {
    // ignore write failure
  }
  currentTheme.value = key
  apply(key)
}

const themeMeta = computed(() => themes.find(t => t.key === currentTheme.value))
const isDark = computed(() => !!themeMeta.value?.dark)

export function useTheme() {
  // initialize once — applies the stored theme on first use (SSR-safe: no window
  // outside browser, but this app is client-only)
  if (!initialized && typeof window !== 'undefined') {
    initialized = true
    apply(currentTheme.value)
  }

  return {
    currentTheme,
    themes,
    setTheme,
    themeMeta,
    isDark
  }
}
