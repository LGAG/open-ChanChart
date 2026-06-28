<template>
  <div class="kline-chart" :class="{ 'is-fullscreen': isFullscreen }">
    <div class="chart-toolbar">
      <div class="chan-toggles">
        <label class="toggle-item">
          <input type="checkbox" v-model="showPens" @change="updateChart" />
          <span class="toggle-indicator" style="background: #0000FF;"></span>
          笔
        </label>
        <label class="toggle-item">
          <input type="checkbox" v-model="showFractals" @change="updateChart" />
          <span class="toggle-indicator" style="background: linear-gradient(135deg, #FF0000 50%, #00FF00 50%);"></span>
          分型
        </label>
        <label class="toggle-item">
          <input type="checkbox" v-model="showSegments" @change="updateChart" />
          <span class="toggle-indicator" style="background: #FF6600;"></span>
          段
        </label>
        <label class="toggle-item">
          <input type="checkbox" v-model="showZhongshu" @change="updateChart" />
          <span class="toggle-indicator" style="background: repeating-linear-gradient(90deg, rgba(255,0,0,0.3) 0 4px, transparent 4px 8px); border: 1px solid rgba(0,0,0,0.15);"></span>
          中枢
        </label>
      </div>
      <button class="fullscreen-btn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏展示'">
        <svg v-if="!isFullscreen" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
          <path d="M3 3h6v2H5v4H3V3zm12 0h6v6h-2V5h-4V3zM3 15h2v4h4v2H3v-6zm16 4h-4v2h6v-6h-2v4z"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
          <path d="M9 3H7v4H3v2h6V3zm8 0h-2v6h6V7h-4V3zM9 21v-6H3v2h4v4h2zm8-4h4v-2h-6v6h2v-4z"/>
        </svg>
      </button>
    </div>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  klineData: {
    type: Array,
    default: () => []
  },
  chanData: {
    type: Object,
    default: () => ({})
  }
})

const chartRef = ref(null)
let chartInstance = null
const isFullscreen = ref(false)

// Visibility toggles for Chan theory structures
const showPens = ref(true)
const showFractals = ref(true)
const showSegments = ref(true)
const showZhongshu = ref(true)

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
  document.body.style.overflow = isFullscreen.value ? 'hidden' : ''
  nextTick(() => {
    if (chartInstance) {
      chartInstance.resize()
    }
  })
}

const handleEscape = (e) => {
  if (e.key === 'Escape' && isFullscreen.value) {
    toggleFullscreen()
  }
}

const initChart = () => {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chartInstance || !props.klineData.length) return

  // Prepare K-line data
  const dates = props.klineData.map(item => item.date)
  const ohlc = props.klineData.map(item => [
    item.open,
    item.close,
    item.low,
    item.high
  ])
  const volumes = props.klineData.map(item => item.volume)

  // Prepare Chan theory data - pen lines as segments
  const penLineData = []
  if (showPens.value && props.chanData.pens) {
    props.chanData.pens.forEach(pen => {
      props.chanData.chan_klines[pen.start_index].start
      if (pen.direction === 'up') {
        penLineData.push([pen.start_date, props.chanData.chan_klines[pen.start_index].low])
        penLineData.push([pen.end_date, props.chanData.chan_klines[pen.end_index].high])
      } else {
        penLineData.push([pen.start_date, props.chanData.chan_klines[pen.start_index].high])
        penLineData.push([pen.end_date, props.chanData.chan_klines[pen.end_index].low])
      }
      penLineData.push([null, null]) // Break line between pens
    })
  }

  // Prepare segment lines - connected as a continuous polyline
  const segmentLineData = []
  if (showSegments.value && props.chanData.segments && props.chanData.pens) {
    props.chanData.segments.forEach((seg, i) => {
      const startPen = props.chanData.pens[seg.start_index]
      const endPen = props.chanData.pens[seg.end_index]
      if (startPen && endPen) {
        const startX = startPen.start_date
        const endX = endPen.end_date
        let startY, endY
        if (seg.direction === 'up') {
          startY = props.chanData.chan_klines[startPen.start_index].low
          endY = props.chanData.chan_klines[endPen.end_index].high
        } else {
          startY = props.chanData.chan_klines[startPen.start_index].high
          endY = props.chanData.chan_klines[endPen.end_index].low
        }
        // First segment: push start point
        if (i === 0) {
          segmentLineData.push([startX, startY])
        }
        // Always push end point — connects to previous segment
        segmentLineData.push([endX, endY])
      }
    })
  }

  // Prepare fractal markers
  const topFractals = []
  const bottomFractals = []
  if (showFractals.value && props.chanData.fractals) {
    props.chanData.fractals.forEach(fractal => {
      if (fractal.type === 'top') {
        topFractals.push([fractal.date, props.chanData.chan_klines[fractal.index].high])
      } else {
        bottomFractals.push([fractal.date, props.chanData.chan_klines[fractal.index].low])
      }
    })
  }

  // Prepare zhongshu rectangles
  const zhongshuSeries = []
  if (showZhongshu.value && props.chanData.zhongshus) {
    props.chanData.zhongshus.forEach((zs, index) => {
      const startKline = props.klineData[zs.start_index]
      const endKline = props.klineData[zs.end_index]
      if (startKline && endKline) {
        zhongshuSeries.push({
          type: 'line',
          name: `中枢${index + 1}上沿`,
          data: dates.map((date, idx) => {
            if (idx >= zs.start_index && idx <= zs.end_index) {
              return zs.high
            }
            return null
          }),
          lineStyle: {
            color: 'rgba(255, 0, 0, 0.3)',
            width: 2,
            type: 'dashed'
          },
          symbol: 'none'
        })
        zhongshuSeries.push({
          type: 'line',
          name: `中枢${index + 1}下沿`,
          data: dates.map((date, idx) => {
            if (idx >= zs.start_index && idx <= zs.end_index) {
              return zs.low
            }
            return null
          }),
          lineStyle: {
            color: 'rgba(0, 255, 0, 0.3)',
            width: 2,
            type: 'dashed'
          },
          symbol: 'none'
        })
      }
    })
  }

  // Build legend entries based on visibility
  const legendData = ['K线']
  if (showPens.value) legendData.push('笔')
  if (showSegments.value) legendData.push('段')
  if (showFractals.value) {
    legendData.push('顶分型')
    legendData.push('底分型')
  }

  const option = {
    title: {
      text: '缠论K线图',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: legendData,
      top: 30
    },
    grid: [
      {
        left: '10%',
        right: '10%',
        top: '15%',
        height: '60%'
      },
      {
        left: '10%',
        right: '10%',
        top: '78%',
        height: '15%'
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ],
    yAxis: [
      {
        scale: true,
        splitArea: {
          show: true
        }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 0,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1],
        type: 'slider',
        top: '93%',
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        itemStyle: {
          color: '#ef232a',
          color0: '#14b143',
          borderColor: '#ef232a',
          borderColor0: '#14b143'
        }
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        itemStyle: {
          color: function(params) {
            const index = params.dataIndex
            if (index === 0) return '#14b143'
            return ohlc[index][1] >= ohlc[index][0] ? '#ef232a' : '#14b143'
          }
        }
      },
      ...zhongshuSeries
    ]
  }

  // Add pen lines
  if (penLineData.length > 0) {
    option.series.push({
      name: '笔',
      type: 'line',
      data: penLineData,
      lineStyle: {
        color: '#0000FF',
        width: 2
      },
      symbol: 'circle',
      symbolSize: 6,
      connectNulls: false
    })
  }

  // Add segment lines (connected polyline)
  if (segmentLineData.length > 0) {
    option.series.push({
      name: '段',
      type: 'line',
      data: segmentLineData,
      lineStyle: {
        color: '#FF6600',
        width: 3
      },
      symbol: 'diamond',
      symbolSize: 8,
      connectNulls: false
    })
  }

  // Add fractal markers
  if (topFractals.length > 0) {
    option.series.push({
      name: '顶分型',
      type: 'scatter',
      data: topFractals,
      symbol: 'triangle',
      symbolSize: 10,
      symbolRotate: 180,
      itemStyle: {
        color: '#FF0000'
      }
    })
  }

  if (bottomFractals.length > 0) {
    option.series.push({
      name: '底分型',
      type: 'scatter',
      data: bottomFractals,
      symbol: 'triangle',
      symbolSize: 10,
      itemStyle: {
        color: '#00FF00'
      }
    })
  }

  chartInstance.setOption(option, true)
}

watch(() => [props.klineData, props.chanData], () => {
  updateChart()
}, { deep: true })

// Handle window resize
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

onMounted(() => {
  nextTick(() => {
    initChart()
  })
  window.addEventListener('resize', handleResize)
  document.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('keydown', handleEscape)
  document.body.style.overflow = ''
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.kline-chart {
  width: 100%;
  position: relative;
}

.chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}

.chan-toggles {
  display: flex;
  gap: 16px;
  align-items: center;
}

.toggle-item {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  user-select: none;
}

.toggle-item input[type="checkbox"] {
  margin: 0;
  cursor: pointer;
  width: 15px;
  height: 15px;
  accent-color: #409eff;
}

.toggle-indicator {
  display: inline-block;
  width: 14px;
  height: 4px;
  border-radius: 2px;
  flex-shrink: 0;
}

.fullscreen-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #fff;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.fullscreen-btn:hover {
  color: #409eff;
  border-color: #409eff;
}

.chart-container {
  width: 100%;
  height: 600px;
}

/* Fullscreen overlay styles */
.kline-chart.is-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  background: #fff;
  padding: 0 16px;
}

.kline-chart.is-fullscreen .chart-container {
  height: calc(100% - 48px);
}

.kline-chart.is-fullscreen .chart-toolbar {
  padding: 8px 0;
}

.kline-chart.is-fullscreen .fullscreen-btn {
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
</style>
