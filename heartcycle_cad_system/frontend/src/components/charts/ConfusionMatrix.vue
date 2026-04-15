<template>
  <div ref="chartRef" :style="{ height, width: '100%' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  // [[TN, FP], [FN, TP]]
  matrix: { type: Array, default: () => [[0, 0], [0, 0]] },
  height: { type: String, default: '360px' }
})

const chartRef = ref(null)
let chartInstance = null

function initChart() {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const m = props.matrix
  const tn = m?.[0]?.[0] ?? 0
  const fp = m?.[0]?.[1] ?? 0
  const fn = m?.[1]?.[0] ?? 0
  const tp = m?.[1]?.[1] ?? 0
  const total = tn + fp + fn + tp || 1

  // 行总数用于计算百分比
  const row0 = tn + fp || 1
  const row1 = fn + tp || 1

  // echarts heatmap data: [x, y, value]
  // x轴=预测，y轴=实际（倒序显示，让(0,0)在左上）
  const data = [
    { value: [0, 1, tn], label: 'TN', pct: ((tn / row0) * 100).toFixed(1), bg: '#67C23A' },
    { value: [1, 1, fp], label: 'FP', pct: ((fp / row0) * 100).toFixed(1), bg: '#F56C6C' },
    { value: [0, 0, fn], label: 'FN', pct: ((fn / row1) * 100).toFixed(1), bg: '#E6A23C' },
    { value: [1, 0, tp], label: 'TP', pct: ((tp / row1) * 100).toFixed(1), bg: '#409EFF' }
  ]

  // 构建用于显示的 heatmap 数据（归一化到 0-100）
  const heatData = data.map(d => [d.value[0], d.value[1], (d.value[2] / total) * 100])

  const option = {
    backgroundColor: '#fff',
    title: {
      text: '混淆矩阵',
      left: 'center', top: 8,
      textStyle: { fontSize: 15, fontWeight: 'bold', color: '#303133' }
    },
    tooltip: {
      formatter: (p) => {
        const d = data[p.dataIndex]
        return `<b>${d.label}</b><br/>数量: ${d.value[2]}<br/>占比: ${d.pct}%`
      }
    },
    grid: { left: '18%', right: '5%', bottom: '18%', top: '18%' },
    xAxis: {
      type: 'category',
      data: ['预测：低风险', '预测：高风险'],
      axisLabel: { fontSize: 12 },
      splitArea: { show: true }
    },
    yAxis: {
      type: 'category',
      data: ['实际：高风险', '实际：低风险'],
      axisLabel: { fontSize: 12 },
      splitArea: { show: true }
    },
    visualMap: {
      min: 0, max: 60,
      calculable: false,
      show: false,
      inRange: { color: ['#EFF8FF', '#BEDDF8', '#409EFF'] }
    },
    series: [{
      type: 'heatmap',
      data: heatData,
      label: {
        show: true,
        formatter: (p) => {
          const d = data[p.dataIndex]
          return `{bold|${d.label}}\n${d.value[2]}\n(${d.pct}%)`
        },
        rich: {
          bold: { fontWeight: 'bold', fontSize: 14, color: '#303133' }
        },
        fontSize: 13,
        color: '#303133',
        lineHeight: 20
      },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' } }
    }]
  }

  chartInstance.setOption(option)
}

const resize = () => chartInstance?.resize()
onMounted(() => { initChart(); window.addEventListener('resize', resize) })
onUnmounted(() => { window.removeEventListener('resize', resize); chartInstance?.dispose() })
watch(() => props.matrix, initChart, { deep: true })
</script>
