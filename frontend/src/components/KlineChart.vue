<template>
  <div class="kline-chart">
    <div ref="chartRef" style="width: 100%; height: 600px;"></div>
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

const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chartInstance || !props.klineData.length) return

  // Build a map from kline index to kline for quick lookup
  const klineMap = {}
  props.klineData.forEach(kline => {
    klineMap[kline.index] = kline
  })

  // Prepare K-line data from ClassicChanKline (start date, high/low only)
  const dates = props.klineData.map(item => item.start)
  // Render as candlestick using high/low (open=low, close=high to show full range bar)
  const ohlc = props.klineData.map(item => [
    item.low,
    item.high,
    item.low,
    item.high
  ])

  // Prepare Chan theory data - pen lines as segments
  const penLineData = []
  if (props.chanData.pens) {
    props.chanData.pens.forEach(pen => {
      const startKline = klineMap[pen.start_index]
      const endKline = klineMap[pen.end_index]
      if (startKline && endKline) {
        const startPrice = pen.direction === 'down' ? startKline.high : startKline.low
        const endPrice = pen.direction === 'down' ? endKline.low : endKline.high
        penLineData.push([pen.start_date, startPrice])
        penLineData.push([pen.end_date, endPrice])
        penLineData.push([null, null]) // Break line between pens
      }
    })
  }

  // Prepare fractal markers
  const topFractals = []
  const bottomFractals = []
  if (props.chanData.fractals) {
    props.chanData.fractals.forEach(fractal => {
      const kline = klineMap[fractal.index]
      if (kline) {
        if (fractal.type === 'top') {
          topFractals.push([kline.start, kline.high])
        } else {
          bottomFractals.push([kline.start, kline.low])
        }
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
      data: ['K线', '笔', '顶分型', '底分型'],
      top: 30
    },
    grid: [
      {
        left: '10%',
        right: '10%',
        top: '15%',
        bottom: '15%'
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
      }
    ],
    yAxis: [
      {
        scale: true,
        splitArea: {
          show: true
        }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0],
        start: 0,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0],
        type: 'slider',
        bottom: '3%',
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
      }
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
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.kline-chart {
  width: 100%;
}
</style>
