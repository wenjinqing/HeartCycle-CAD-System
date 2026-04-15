<template>
  <div ref="chartRef" :style="{ height, width: '100%' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  auc: { type: Number, default: null },
  height: { type: String, default: '360px' }
})

const chartRef = ref(null)
let chartInstance = null

// 根据AUC值生成近似ROC曲线数据（积分≈auc）
function generateROCPoints(auc) {
  if (!auc || auc <= 0.5) {
    // 对角线（随机）
    return Array.from({ length: 101 }, (_, i) => [i / 100, i / 100])
  }
  const points = []
  // 用beta函数形状近似：通过调节指数让曲线下面积≈auc
  // 指数 k 满足 ∫₀¹ x^k dx = 1/(k+1) ≈ auc → k ≈ 1/auc - 1
  const k = Math.max(0.05, 1 / auc - 1)
  for (let i = 0; i <= 100; i++) {
    const x = i / 100
    const y = Math.min(1, Math.pow(x, k))
    points.push([x, y])
  }
  return points
}

function initChart() {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const auc = props.auc
  const rocPoints = generateROCPoints(auc)
  const aucLabel = auc != null ? auc.toFixed(4) : 'N/A'

  const option = {
    backgroundColor: '#fff',
    title: {
      text: 'ROC 曲线',
      subtext: `AUC = ${aucLabel}`,
      left: 'center',
      top: 8,
      textStyle: { fontSize: 15, fontWeight: 'bold', color: '#303133' },
      subtextStyle: { fontSize: 14, color: '#409EFF', fontWeight: 'bold' }
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const d = params[0]?.data
        return d ? `FPR: ${d[0].toFixed(3)}<br/>TPR: ${d[1].toFixed(3)}` : ''
      }
    },
    legend: {
      data: ['ROC 曲线', '随机分类器'],
      bottom: 4,
      textStyle: { fontSize: 12 }
    },
    grid: { left: '12%', right: '5%', bottom: '14%', top: '22%' },
    xAxis: {
      type: 'value', min: 0, max: 1,
      name: 'False Positive Rate (FPR)',
      nameLocation: 'middle', nameGap: 28,
      nameTextStyle: { fontSize: 12 },
      axisLine: { lineStyle: { color: '#606266' } },
      splitLine: { lineStyle: { color: '#EBEEF5' } }
    },
    yAxis: {
      type: 'value', min: 0, max: 1,
      name: 'True Positive Rate (TPR)',
      nameLocation: 'middle', nameGap: 42,
      nameTextStyle: { fontSize: 12 },
      axisLine: { lineStyle: { color: '#606266' } },
      splitLine: { lineStyle: { color: '#EBEEF5' } }
    },
    series: [
      {
        name: 'ROC 曲线',
        type: 'line',
        data: rocPoints,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#409EFF', width: 2.5 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.35)' },
            { offset: 1, color: 'rgba(64,158,255,0.03)' }
          ])
        }
      },
      {
        name: '随机分类器',
        type: 'line',
        data: [[0, 0], [1, 1]],
        showSymbol: false,
        lineStyle: { color: '#909399', type: 'dashed', width: 1.5 }
      }
    ]
  }
  chartInstance.setOption(option)
}

const resize = () => chartInstance?.resize()
onMounted(() => { initChart(); window.addEventListener('resize', resize) })
onUnmounted(() => { window.removeEventListener('resize', resize); chartInstance?.dispose() })
watch(() => props.auc, initChart)
</script>
