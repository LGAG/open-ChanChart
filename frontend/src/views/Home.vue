<template>
  <div class="home">
    <el-card class="control-panel">
      <h2>可视化系统</h2>
      
      <div class="controls">
        <div class="control-item">
          <label>选择股票：</label>
          <StockSelector @change="handleStockChange" />
        </div>

        <div class="control-item">
          <label>选择周期：</label>
          <el-radio-group v-model="period" @change="loadData">
            <el-radio-button label="daily">日K</el-radio-button>
            <el-radio-button label="60F">1小时</el-radio-button>
            <el-radio-button label="30F">30分</el-radio-button>
          </el-radio-group>
        </div>

        <div class="control-item">
          <label>时间范围：</label>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="loadData"
            style="width: 260px"
            default-time="00:00:00"
          />
        </div>

        <div class="control-item">
          <el-button type="primary" @click="loadData" :loading="loading">
            刷新数据
          </el-button>
          <el-button type="success" @click="handleRefreshStockList" :loading="refreshingList">
            更新股票列表
          </el-button>
          <el-button type="warning" @click="handleUpdateKline" :loading="updatingKline" :disabled="!currentStock">
            更新K线数据
          </el-button>
        </div>
      </div>

      <div class="info" v-if="currentStock">
        <el-tag>{{ currentStock.code }} - {{ currentStock.name }}</el-tag>
        <el-tag type="info" style="margin-left: 10px">{{ currentStock.market === 'sh' ? '上海' : '深圳' }}</el-tag>
      </div>
    </el-card>

    <el-card class="chart-panel" v-loading="loading">
      <KlineChart 
        v-if="klineData.length > 0"
        :klineData="klineData"
        :chanData="chanData"
      />
      <el-empty v-else description="请选择股票查看图表" />
    </el-card>

    <el-card class="stats-panel" v-if="chanData.pens">
      <h3>缠论数据统计</h3>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="分型数量" :value="chanData.fractals?.length || 0" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="笔数量" :value="chanData.pens?.length || 0" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="段数量" :value="chanData.segments?.length || 0" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="中枢数量" :value="chanData.zhongshus?.length || 0" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import KlineChart from '../components/KlineChart.vue'
import StockSelector from '../components/StockSelector.vue'
import { getChanAnalysis } from '../api/chan'
import { refreshStockList, updateKlineData } from '../api/stock'

interface Stock {
  code: string
  name: string
  market: 'sh' | 'sz'
}

const currentStock = ref<Stock | null>(null)
const period = ref('daily')
const loading = ref(false)
const refreshingList = ref(false)
const updatingKline = ref(false)
const klineData = ref<any[]>([])
const chanData = ref<{
  fractals?: any[]
  pens?: any[]
  segments?: any[]
  zhongshus?: any[]
}>({})
const dateRange = ref<[string, string]>([
  new Date(new Date().setMonth(new Date().getMonth() - 6)).toISOString().slice(0, 10),
  new Date().toISOString().slice(0, 10)
])

const handleStockChange = (stock: Stock) => {
  currentStock.value = stock
  loadData()
}

const handleRefreshStockList = async () => {
  refreshingList.value = true
  try {
    const response = await refreshStockList()
    if (response?.code === 200) {
      ElMessage.success(response.message || '股票列表更新成功')
    } else {
      ElMessage.error(response?.message || '股票列表更新失败')
    }
  } catch (error: any) {
    ElMessage.error(`更新失败：${error?.message || '未知错误'}`)
  } finally {
    refreshingList.value = false
  }
}

const handleUpdateKline = async () => {
  if (!currentStock.value) {
    ElMessage.warning('请先选择股票')
    return
  }
  updatingKline.value = true
  try {
    const params: Record<string, string> = {
      code: currentStock.value.code,
      name: currentStock.value.name,
      market: currentStock.value.market
    }
    if (dateRange.value && dateRange.value[0]) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const response = await updateKlineData(params)
    if (response?.code === 200) {
      ElMessage.success('K线数据更新成功')
      loadData()
    } else {
      ElMessage.error(response?.message || 'K线数据更新失败')
    }
  } catch (error: any) {
    ElMessage.error(`更新失败：${error?.message || '未知错误'}`)
  } finally {
    updatingKline.value = false
  }
}

const loadData = async () => {
  if (!currentStock.value) {
    ElMessage.warning('请先选择股票')
    return
  }

  loading.value = true
  try {
    // 拼接请求参数（新增时间范围）
    const params = {
      code: currentStock.value.code,
      name: currentStock.value.name,
      market: currentStock.value.market,
      period: period.value,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1]
    }

    const response = await getChanAnalysis(params)
    
    // 增强响应数据容错
    if (response?.code === 200 && response?.data) {
      klineData.value = response.data.klines || []
      chanData.value = response.data.chan || {}
      ElMessage.success('数据加载成功')
    } else {
      ElMessage.error('数据加载失败：接口返回异常')
    }
  } catch (error: any) {
    ElMessage.error(`请求失败：${error?.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.home {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.control-panel {
  margin-bottom: 20px;
}

.control-panel h2 {
  margin: 0 0 20px 0;
  color: #409eff;
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 20px;
}

.control-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-item label {
  font-weight: 500;
  white-space: nowrap;
}

.info {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.chart-panel {
  margin-bottom: 20px;
}

.stats-panel h3 {
  margin: 0 0 20px 0;
}
</style>