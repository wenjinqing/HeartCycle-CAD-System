<template>
  <div ref="chartRef" :style="{ height, width: '100%' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  // metrics: { accuracy:{mean,std,scores}, precision:{...}, recall:{...}, f1:{...}, roc_auc:{...} }
  metrics: { type: Object, default: () => ({}) },
  height: { type: String, default: '360px' }
})

const chartRef = ref(null)
let chartInstance = null

const METRIC_CONFIG = [
  { key: 'accuracy', label: '准确率', color: '#409EFF' },
  { key: 'precision', label: '精确率', color: '#67C23A' },
  { key: 'recall', label: '召回率', color: '#E6A23C' },
  { key: 'f1', label: 'F1 分数', color: '#F56C6C' },
  { key: 'roc_auc', label: 'ROC AUC', color: '#9B59B6' }
]

function initChart() {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const series = []
  const legendData = []
  let folds = 0

  METRIC_CONFIG.forEach(({ key, label, color }) => {
    const m = props.metrics?.[key]
    const scores = m?.scores?.filter(v => v != null)
    if (!scores || scores.length === 0) return
    folds = Math.max(folds, scores.length)
    legendData.push(label)

    // 主折线
    series.push({
      name: label,
      type: 'line',
      data: scores,
      smooth: true,
      symbol: 'circle',
      symbolSize: 7,
      lineStyle: { color, width: 2 },
      itemStyle: { color },
      // 均值标注线
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color, type: 'dashed', width: 1.2, opacity: 0.6 },
        data: [{ type: 'average', name: `均值 ${label}` }],
        label: {
          formatter: (p) => `均值: ${p.value.toFixed(4)}`,
          fontSize: 11
        }
      }
    })
  })

  const xData = Array.from({ length: folds }, (_, i) => `Fold ${i + 1}`)

  const option = {
    backgroundColor: '#fff',
    title: {
      text: '交叉验证各折性能',
      left: 'center', top: 8,
      textStyle: { fontSize: 15, fontWeight: 'bold', color: '#303133' }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = `<b>${params[0].axisValue}</b><br/>`
        params.forEach(p => {
          html += `${p.marker}${p.seriesName}: <b>${p.value.toFixed(4)}</b><br/>`
        })
        return html
      }
    },
    legend: {
      data: legendData,
      bottom: 4,
      textStyle: { fontSize: 11 }
    },
    grid: { left: '8%', right: '3%', bottom: '14%', top: '16%' },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      min: (v) => Math.max(0, (v.min - 0.05).toFixed(2) * 1),
      max: 1,
      axisLabel: { formatter: (v) => v.toFixed(2), fontSize: 11 },
      splitLine: { lineStyle: { color: '#EBEEF5' } }
    },
    series
  }
  chartInstance.setOption(option)
}

const resize = () => chartInstance?.resize()
onMounted(() => { initChart(); window.addEventListener('resize', resize) })
onUnmounted(() => { window.removeEventListener('resize', resize); chartInstance?.dispose() })
watch(() => props.metrics, initChart, { deep: true })
</script>
