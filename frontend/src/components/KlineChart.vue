<template>
  <Teleport to="body" :disabled="!isFullscreen">
    <div class="kline-chart" :class="{ 'is-fullscreen': isFullscreen }">
      <div class="chart-toolbar">
        <div class="chan-toggles">
          <!-- 一行排开:每个结构一组 = 勾选框(带字,是否参与计算)+ 无字色块按钮(series 显隐) -->
          <div
            v-for="btn in seriesToggleBtns"
            :key="btn.key"
            class="toggle-group"
          >
            <label class="toggle-item">
              <input
                type="checkbox"
                :checked="showVar(btn.showKey).value"
                @change="showVar(btn.showKey).value = $event.target.checked; updateChart()"
              />
              <span class="toggle-indicator" :style="indicatorStyle(btn)"></span>
              {{ btn.label }}
            </label>
            <button
              class="series-btn"
              :class="{ active: !seriesHidden[btn.key], disabled: !isSeriesToggleable(btn.key) }"
              :style="btnStyle(btn)"
              :disabled="!isSeriesToggleable(btn.key)"
              :title="btn.label + (seriesHidden[btn.key] ? '(已隐藏)' : '(显示/隐藏)')"
              @click="toggleSeries(btn.key)"
            >
              <span class="series-btn-icon" :style="iconStyle(btn)"></span>
            </button>
          </div>
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
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { useTheme } from '../composables/useTheme'

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

// 用户当前缩放(由 dataZoom 事件实时保存)。toggle 显隐时回写以保留缩放;
// 换股票时清空(null)重置回整个周期。null → 用默认 0~100。
const savedZoom = ref(null)

// Theme-driven color palette (re-renders chart on theme change)
const { currentTheme, themeMeta } = useTheme()
const palette = computed(() => themeMeta.value.echarts)

// Visibility toggles for Chan theory structures (checkboxes — 是否参与计算)
const showPens = ref(true)
const showFractals = ref(false)
const showSegments = ref(true)
const showZhongshu = ref(true)

// 图形按钮(series 显隐):点亮=显示该类别所有 series,熄灭=隐藏。
// 与勾选框是从属关系:勾选框关闭时对应按钮禁用(无数据可显隐)。
// key 取缠论结构类别名,与左侧 toolbar 的图形按钮一一对应。
const seriesHidden = ref({
  pen: false,
  fractal: false,
  segment: false,
  zhongshu: false
})
const toggleSeries = (key) => {
  seriesHidden.value[key] = !seriesHidden.value[key]
  updateChart()
}
// 某类别图形按钮是否可点:仅当对应勾选框开启(该类别参与计算)时才生效
const isSeriesToggleable = (key) => {
  switch (key) {
    case 'pen': return showPens.value
    case 'fractal': return showFractals.value
    case 'segment': return showSegments.value
    case 'zhongshu': return showZhongshu.value
    default: return false
  }
}

// 每个缠论结构一组控件:勾选框(带字,是否参与计算)+ 无字色块按钮(series 显隐)。
// showKey 映射到对应的 showXxx 响应式变量;key 映射到 seriesHidden 字段。
const seriesToggleBtns = [
  { key: 'pen', showKey: 'pens', label: '笔' },
  { key: 'fractal', showKey: 'fractals', label: '分型' },
  { key: 'segment', showKey: 'segments', label: '段' },
  { key: 'zhongshu', showKey: 'zhongshu', label: '中枢' }
]

// 勾选框绑定的响应式变量(showPens/showFractals/...)— v-model 不能用计算式,需显式 get/set
const showVar = (showKey) => {
  switch (showKey) {
    case 'pens': return showPens
    case 'fractals': return showFractals
    case 'segments': return showSegments
    case 'zhongshu': return showZhongshu
    default: return showPens
  }
}

// 按钮点亮时的主题色。分型由顶/底两色组成,故区分:
//   solidColor — 纯色,用于边框/发光(boxShadow/border-color 不支持 gradient)
//   iconBg     — icon 背景,可用 gradient(分型用顶底渐变区分)
const solidColor = (btn) => {
  const p = palette.value
  switch (btn.key) {
    case 'pen': return p.pen
    case 'fractal': return p.up
    case 'segment': return p.seg
    case 'zhongshu': return p.zsh
    default: return p.accent
  }
}
const iconBg = (btn) => {
  const p = palette.value
  if (btn.key === 'fractal') return `linear-gradient(135deg, ${p.up} 50%, ${p.down} 50%)`
  return solidColor(btn)
}
const btnStyle = (btn) => {
  const on = !seriesHidden.value[btn.key] && isSeriesToggleable(btn.key)
  return {
    borderColor: on ? solidColor(btn) : 'var(--panel-border)',
    color: on ? 'var(--text)' : 'var(--text-dim)'
  }
}
const iconStyle = (btn) => {
  const on = !seriesHidden.value[btn.key] && isSeriesToggleable(btn.key)
  return {
    background: on ? iconBg(btn) : 'transparent',
    boxShadow: on ? '0 0 6px ' + solidColor(btn) : 'none'
  }
}

// 勾选框旁的色条指示器:复刻原写死颜色(笔/段/中枢纯色+发光,分型顶底渐变)
const indicatorStyle = (btn) => {
  const p = palette.value
  switch (btn.key) {
    case 'pen': return { background: p.pen, boxShadow: '0 0 6px ' + p.pen }
    case 'fractal': return { background: `linear-gradient(135deg, ${p.up} 50%, ${p.down} 50%)` }
    case 'segment': return { background: p.seg, boxShadow: '0 0 6px ' + p.seg }
    case 'zhongshu': return { background: `repeating-linear-gradient(90deg, ${p.zsh} 0 4px, transparent 4px 8px)` }
    default: return {}
  }
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
  document.body.style.overflow = isFullscreen.value ? 'hidden' : ''
  // 全屏切换会触发 Teleport 移动 DOM + CSS 重排，需等重排完成后再 resize。
  // nextTick 保证 DOM 已移动，requestAnimationFrame 保证布局已结算出正确尺寸。
  nextTick(() => {
    requestAnimationFrame(() => {
      if (chartInstance) {
        chartInstance.resize()
      }
    })
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
  // 用户每次缩放(滑块/滚轮)实时保存 start/end,toggle 显隐重建 option 时回写,
  // 避免缩放被重置回整个周期。
  chartInstance.on('dataZoom', () => {
    const dz = chartInstance.getOption().dataZoom
    if (dz && dz.length) {
      savedZoom.value = { start: dz[0].start, end: dz[0].end }
    }
  })
  updateChart()
}

const updateChart = (preserveZoom = true) => {
  if (!chartInstance || !props.klineData.length) return

  const p = palette.value

  // 保留用户当前缩放:toggle 缠论结构显隐会整体重建 option(setOption notMerge),
  // 若不回写 dataZoom 的 start/end,ECharts 会重置回 0~100(整个周期),丢失缩放。
  // 缩放值由 dataZoom 事件实时存入 savedZoom(ref),updateChart 读取回写,
  // 避免在首次渲染时对空实例调 getOption()。
  // 换股票/换周期(preserveZoom=false)时清空 savedZoom 重置回全量。
  if (!preserveZoom) {
    savedZoom.value = null
  }
  const zoomStart = savedZoom.value ? savedZoom.value.start : 0
  const zoomEnd = savedZoom.value ? savedZoom.value.end : 100

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
  const virtualPenLineData = []
  if (showPens.value && props.chanData.pens) {
    props.chanData.pens.forEach(pen => {
      props.chanData.chan_klines[pen.start_index].start
      const seg = []
      if (pen.direction === 'up') {
        seg.push([pen.start_date, props.chanData.chan_klines[pen.start_index].low])
        seg.push([pen.end_date, props.chanData.chan_klines[pen.end_index].high])
      } else {
        seg.push([pen.start_date, props.chanData.chan_klines[pen.start_index].high])
        seg.push([pen.end_date, props.chanData.chan_klines[pen.end_index].low])
      }
      const target = pen.is_sure === false ? virtualPenLineData : penLineData
      target.push(seg[0])
      target.push(seg[1])
      target.push([null, null]) // Break line between pens
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

  // Prepare zhongshu rectangles (markArea)
  // 注意：zs.start_index / zs.end_index 是「缠论K线索引」，需经 chan_klines 映射回
  // 原始K线索引区间（chan_klines[idx].start ~ .end），才能对齐到 dates 数组。
  const zhongshuMarkAreas = []
  if (showZhongshu.value && !seriesHidden.value.zhongshu && props.chanData.zhongshus && props.chanData.chan_klines) {
    props.chanData.zhongshus.forEach((zs, index) => {
      const startChanK = props.chanData.chan_klines[zs.start_index]
      const endChanK = props.chanData.chan_klines[zs.end_index]
      if (!startChanK || !endChanK) return
      const rawStart = startChanK.start  // 原始K线索引
      const rawEnd = endChanK.end        // 原始K线索引
      if (rawStart == null || rawEnd == null) return
      zhongshuMarkAreas.push([
        {
          xAxis: dates[rawStart],
          yAxis: zs.low
        },
        {
          xAxis: dates[rawEnd],
          yAxis: zs.high
        }
      ])
    })
  }

  const option = {
    backgroundColor: p.bg,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: { color: p.axis }
      },
      backgroundColor: 'rgba(10, 10, 20, 0.9)',
      borderColor: p.axis,
      borderWidth: 1,
      textStyle: { color: p.text }
    },
    grid: [
      {
        left: '8%',
        right: '5%',
        top: '4%',
        height: '68%'
      },
      {
        left: '8%',
        right: '5%',
        top: '75%',
        height: '14%'
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false, lineStyle: { color: p.axis } },
        axisLabel: { color: p.text },
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
        axisLine: { onZero: false, lineStyle: { color: p.axis } },
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
        axisLine: { lineStyle: { color: p.axis } },
        axisLabel: { color: p.text },
        splitLine: { lineStyle: { color: p.split } },
        splitArea: {
          show: true,
          areaStyle: { color: ['transparent', p.split] }
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
        start: zoomStart,
        end: zoomEnd
      },
      {
        show: true,
        xAxisIndex: [0, 1],
        type: 'slider',
        top: '93%',
        start: zoomStart,
        end: zoomEnd,
        dataBackground: { lineStyle: { color: p.axis }, areaStyle: { color: p.split } },
        fillerColor: p.split,
        borderColor: p.axis,
        textStyle: { color: p.text }
      }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        itemStyle: {
          color: p.up,
          color0: p.down,
          borderColor: p.up,
          borderColor0: p.down
        },
        markArea: {
          silent: true,
          // markArea 仅作视觉标注，不进 tooltip、不显示常驻 label
          // （trigger:'axis' 时常驻 label 会被聚合进 tooltip，导致悬停显示所有中枢）
          label: { show: false },
          data: zhongshuMarkAreas.map(area => [
            {
              xAxis: area[0].xAxis,
              yAxis: area[0].yAxis,
              itemStyle: {
                color: p.zsh,
                borderColor: p.zsl,
                borderWidth: 1.5
              }
            },
            {
              xAxis: area[1].xAxis,
              yAxis: area[1].yAxis
            }
          ])
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
            if (index === 0) return p.down
            return ohlc[index][1] >= ohlc[index][0] ? p.up : p.down
          },
          opacity: 0.6
        }
      }
    ]
  }

  // Add pen lines
  if (penLineData.length > 0 && !seriesHidden.value.pen) {
    option.series.push({
      name: '笔',
      type: 'line',
      data: penLineData,
      lineStyle: {
        color: p.pen,
        width: 2,
        shadowColor: p.pen,
        shadowBlur: 8
      },
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: p.pen },
      connectNulls: false,
      clip: true
    })
  }

  // Add virtual (unconfirmed) pen lines — dashed, follows 笔 toggle
  if (virtualPenLineData.length > 0 && !seriesHidden.value.pen) {
    option.series.push({
      name: '笔(未确认)',
      type: 'line',
      data: virtualPenLineData,
      lineStyle: {
        color: p.pen,
        width: 2,
        type: 'dashed',
        opacity: 0.6,
        shadowColor: p.pen,
        shadowBlur: 4
      },
      symbol: 'circle',
      symbolSize: 5,
      itemStyle: { color: p.pen },
      connectNulls: false,
      clip: true
    })
  }

  // Add segment lines (connected polyline)
  if (segmentLineData.length > 0 && !seriesHidden.value.segment) {
    option.series.push({
      name: '段',
      type: 'line',
      data: segmentLineData,
      lineStyle: {
        color: p.seg,
        width: 3,
        shadowColor: p.seg,
        shadowBlur: 10
      },
      symbol: 'diamond',
      symbolSize: 8,
      itemStyle: { color: p.seg },
      connectNulls: false,
      clip: true
    })
  }

  // Add fractal markers
  if (topFractals.length > 0 && !seriesHidden.value.fractal) {
    option.series.push({
      name: '顶分型',
      type: 'scatter',
      data: topFractals,
      symbol: 'triangle',
      symbolSize: 10,
      symbolRotate: 180,
      itemStyle: {
        color: p.up,
        shadowColor: p.up,
        shadowBlur: 8
      }
    })
  }

  if (bottomFractals.length > 0 && !seriesHidden.value.fractal) {
    option.series.push({
      name: '底分型',
      type: 'scatter',
      data: bottomFractals,
      symbol: 'triangle',
      symbolSize: 10,
      itemStyle: {
        color: p.down,
        shadowColor: p.down,
        shadowBlur: 8
      }
    })
  }

  chartInstance.setOption(option, true)
}

// 换股票/换周期:klineData 引用变化 → 重置缩放回整个周期(看全貌)
watch(() => props.klineData, () => {
  updateChart(false)
}, { deep: true })

// chanData 变化(同股票重新分析等)→ 保留当前缩放
watch(() => props.chanData, () => {
  updateChart(true)
}, { deep: true })

// Re-render with new palette when the theme changes
watch(currentTheme, () => {
  nextTick(updateChart)
})

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
  flex-wrap: wrap;
}

/* 每组:勾选框(带字)+ 紧邻的无字色块按钮 */
.toggle-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toggle-item {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-dim);
  user-select: none;
}

.toggle-item input[type="checkbox"] {
  margin: 0;
  cursor: pointer;
  width: 15px;
  height: 15px;
  accent-color: var(--accent);
}

.toggle-indicator {
  display: inline-block;
  width: 14px;
  height: 4px;
  border-radius: 2px;
  flex-shrink: 0;
}

.series-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border: 1px solid var(--panel-border);
  border-radius: 4px;
  background: var(--panel-bg);
  color: var(--text);
  cursor: pointer;
  user-select: none;
  transition: all 0.15s;
}

.series-btn:hover:not(.disabled) {
  filter: brightness(1.15);
}

.series-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.series-btn-icon {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
  border: 1px solid currentColor;
}

.fullscreen-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--panel-border);
  border-radius: 4px;
  background: var(--panel-bg);
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.fullscreen-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
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
  background: var(--bg);
  padding: 0 16px;
  display: flex;
  flex-direction: column;
}

/* 全屏下 toolbar 自适应高度,图表填满剩余空间(不依赖固定像素差) */
.kline-chart.is-fullscreen .chart-toolbar {
  flex-shrink: 0;
}

.kline-chart.is-fullscreen .chart-container {
  height: auto;
  flex: 1 1 auto;
  min-height: 0;
}

.kline-chart.is-fullscreen .chart-toolbar {
  padding: 8px 0;
}

.kline-chart.is-fullscreen .fullscreen-btn {
  width: 36px;
  height: 36px;
  background: var(--panel-bg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
</style>

<style>
/* ECharts 的 canvas 由 zrender 运行时插入,不带 scoped data 属性,scoped 规则无法命中。
   用全局(非 scoped)规则 + !important 覆盖其 inline cursor,使悬停 K 线图时显示
   小圆圈光标,避免默认大指针遮挡图形(白环+黑描边,深/浅主题下均可见,热点在圆心)。 */
.chart-container canvas {
  cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 20 20'%3E%3Ccircle cx='10' cy='10' r='4' fill='none' stroke='black' stroke-width='3'/%3E%3Ccircle cx='10' cy='10' r='4' fill='none' stroke='white' stroke-width='1'/%3E%3C/svg%3E") 10 10, crosshair !important;
}
</style>
