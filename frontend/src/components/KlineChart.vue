<template>
  <div class="kline-chart" :class="{ 'is-fullscreen': isFullscreen }">
    <div class="chart-actions">
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
  if (props.chanData.pens) {
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

  // Prepare segment lines
  const segmentLineData = []
  if (props.chanData.segments && props.chanData.pens) {
    props.chanData.segments.forEach(seg => {
      const startPen = props.chanData.pens[seg.start_index]
      const endPen = props.chanData.pens[seg.end_index]
      if (startPen && endPen) {
        if (seg.direction === 'up') {
          segmentLineData.push([startPen.start_date, props.chanData.chan_klines[startPen.start_index].low])
          segmentLineData.push([endPen.end_date, props.chanData.chan_klines[endPen.start_index].high])
        } else {
          segmentLineData.push([startPen.start_date, props.chanData.chan_klines[startPen.start_index].high])
          segmentLineData.push([endPen.end_date, props.chanData.chan_klines[endPen.start_index].low])
        }
        segmentLineData.push([null, null]) // Break line between segments
      }
    })
  }

  // Prepare fractal markers
  const topFractals = []
  const bottomFractals = []
  if (props.chanData.fractals) {
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
  if (props.chanData.zhongshus) {
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
      data: ['K线', '笔', '段', '顶分型', '底分型'],
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

  // Add segment lines
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

.chart-container {
  width: 100%;
  height: 600px;
}

.chart-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
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
}

.fullscreen-btn:hover {
  color: #409eff;
  border-color: #409eff;
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
  padding: 0;
}

.kline-chart.is-fullscreen .chart-container {
  height: 100%;
}

.kline-chart.is-fullscreen .chart-actions {
  top: 12px;
  right: 12px;
}

.kline-chart.is-fullscreen .fullscreen-btn {
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
</style>
