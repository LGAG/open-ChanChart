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

  // Prepare fractal markers
  const topFractals = []
  const bottomFractals = []
  if (props.chanData.fractals) {
    props.chanData.fractals.forEach(fractal => {
      if (fractal.type === 'top') {
        topFractals.push([fractal.date, fractal.price])
      } else {
        bottomFractals.push([fractal.date, fractal.price])
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
      data: ['K线', '笔', '顶分型', '底分型'],
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
