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
      style="width: 300px"
    >
      <el-option
        v-for="item in stockList"
        :key="item.code + '|' + item.name"
        :label="`${item.code} - ${item.name}`"
        :value="item.code + '|' + item.name"
      >
        <span>{{ item.code }}</span>
        <span style="float: right; color: #8492a6; font-size: 13px">{{ item.name }}</span>
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

// Initial stock list
stockList.value = [
  { code: '000001', name: '平安银行', market: 'sz' },
  { code: '600519', name: '贵州茅台', market: 'sh' }
]

const handleSearch = async (query) => {
  if (!query) return
  
  loading.value = true
  try {
    const response = await searchStocks(query)
    if (response.code === 200) {
      stockList.value = response.data
    }
  } catch (error) {
    ElMessage.error('搜索失败：' + error.message)
  } finally {
    loading.value = false
  }
}

const handleChange = (value) => {
  const stock = stockList.value.find(s => s.code + '|' + s.name === value)
  if (stock) {
    emit('change', stock)
  }
}
</script>

<style scoped>
.stock-selector {
  margin: 10px 0;
}
</style>
