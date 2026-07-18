<template>
  <div class="stock-selector">
    <el-select
      v-model="selectedStock"
      filterable
      remote
      reserve-keyword
      placeholder="请输入股票代码或名称"
      :remote-method="handleSearch"
      :loading="loading"
      @change="handleChange"
      @visible-change="handleVisibleChange"
      style="width: 300px"
    >
      <el-option
        v-for="item in stockList"
        :key="item.code + '|' + item.name"
        :label="`${item.code} - ${item.name}`"
        :value="item.code + '|' + item.name"
      >
        <span>{{ item.code }}</span>
        <span style="float: right; color: var(--text-dim); font-size: 13px">{{ item.name }}</span>
      </el-option>
    </el-select>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { searchStocks } from '../api/stock'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['change'])

const selectedStock = ref('')
const stockList = ref([])
const loading = ref(false)

// 最近搜索缓存：sessionStorage 临时存储（关标签页即清），选中时写入，搜索框为空时展示。
const RECENT_KEY = 'chanchart_recent_stocks'
const RECENT_MAX = 10

const getRecentStocks = () => {
  try {
    const raw = sessionStorage.getItem(RECENT_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

const addRecentStock = (stock) => {
  if (!stock?.code) return
  const list = getRecentStocks()
  // 去重（按 code+market），把新选中的置顶
  const filtered = list.filter(s => !(s.code === stock.code && s.market === stock.market))
  filtered.unshift({ code: stock.code, name: stock.name, market: stock.market })
  sessionStorage.setItem(RECENT_KEY, JSON.stringify(filtered.slice(0, RECENT_MAX)))
}

// 初始下拉展示：最近搜索（若有），否则默认股票
const defaultStocks = [
  { code: '000001', name: '平安银行', market: 'sz' },
  { code: '600519', name: '贵州茅台', market: 'sh' }
]
stockList.value = (() => {
  const recent = getRecentStocks()
  return recent.length > 0 ? recent : defaultStocks
})()

// 防抖 + 竞态取消：停顿 250ms 才发请求，且新请求发出时取消上一个未完成的请求，
// 避免连按多键产生一串无谓请求、以及旧请求晚返回覆盖新结果。
let debounceTimer = null
let abortController = null

const handleSearch = (query) => {
  if (!query) {
    // 搜索框为空 → 展示最近搜索（若有），否则展示默认股票
    const recent = getRecentStocks()
    stockList.value = recent.length > 0 ? recent : defaultStocks
    return
  }

  // 清掉上一次待发的防抖
  if (debounceTimer) clearTimeout(debounceTimer)

  debounceTimer = setTimeout(async () => {
    // 取消上一个未完成的请求，避免其回调覆盖本次结果
    if (abortController) abortController.abort()
    abortController = new AbortController()

    loading.value = true
    try {
      const response = await searchStocks(query, null, { signal: abortController.signal })
      if (response.code === 200) {
        stockList.value = response.data
      }
    } catch (error) {
      // 被取消的请求会抛 AbortError，静默忽略
      if (error?.name !== 'AbortError') {
        ElMessage.error('搜索失败：' + (error?.message || '未知错误'))
      }
    } finally {
      loading.value = false
    }
  }, 250)
}

// 下拉框展开时，若搜索框为空，刷新为最近搜索（保证每次展开都是最新缓存）
const handleVisibleChange = (visible) => {
  if (visible && !selectedStock.value) {
    const recent = getRecentStocks()
    stockList.value = recent.length > 0 ? recent : defaultStocks
  }
}

const handleChange = (value) => {
  const stock = stockList.value.find(s => s.code + '|' + s.name === value)
  if (stock) {
    addRecentStock(stock)  // 选中即写入最近搜索缓存
    emit('change', stock)
  }
}
</script>

<style scoped>
.stock-selector {
  margin: 10px 0;
}
</style>
