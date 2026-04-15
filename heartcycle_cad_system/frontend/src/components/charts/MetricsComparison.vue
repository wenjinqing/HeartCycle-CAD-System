<template>
  <div ref="chartRef" :style="{ height, width: '100%' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  // metrics: { accuracy, precision, recall, f1, roc_auc }（均值）
  metrics: { type: Object, default: () => ({}) },
  chartType: { type: String, default: 'radar' }, // 'radar' | 'bar'
  height: { type: String, default: '360px' }
})

const chartRef = ref(null)
let chartInstance = null

const LABELS = ['准确率', '精确率', '召回率', 'F1 分数', 'AUC']
const KEYS = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']
const COLORS = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#9B59B6']

function getValues() {
  return KEYS.map(k => {
    const v = props.metrics?.[k]
    return v != null ? parseFloat(v.toFixed(4)) : 0
  })
}

function buildRadar(values) {
  return {
    title: { text: '性能指标雷达图', left: 'center', top: 8, textStyle: { fontSize: 15, fontWeight: 'bold', color: '#303133' } },
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        return LABELS.map((l, i) => `${l}: <b>${p.value[i]?.toFixed(4) ?? 'N/A'}</b>`).join('<br/>')
      }
    },
    radar: {
      shape: 'polygon',
      center: ['50%', '55%'],
      radius: '62%',
      indicator: LABELS.map(name => ({ name, max: 1, min: 0 })),
      splitArea: { areaStyle: { color: ['rgba(64,158,255,0.05)', 'rgba(64,158,255,0.02)'] } },
      axisLine: { lineStyle: { color: '#DCDFE6' } },
      splitLine: { lineStyle: { color: '#EBEEF5' } },
      name: { textStyle: { fontSize: 12, color: '#606266' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: '模型性能',
        areaStyle: { color: 'rgba(64,158,255,0.25)' },
        lineStyle: { color: '#409EFF', width: 2 },
        itemStyle: { color: '#409EFF' },
        symbol: 'circle', symbolSize: 6
      }]
    }]
  }
}

function buildBar(values) {
  return {
    title: { text: '性能指标对比', left: 'center', top: 8, textStyle: { fontSize: 15, fontWeight: 'bold', color: '#303133' } },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `${p.name}: <b>${p.value.toFixed(4)}</b>`
      }
    },
    grid: { left: '10%', right: '5%', bottom: '14%', top: '18%' },
    xAxis: {
      type: 'category',
      data: LABELS,
      axisLabel: { fontSize: 12, color: '#606266' }
    },
    yAxis: {
      type: 'value', min: 0, max: 1,
      axisLabel: { formatter: (v) => v.toFixed(1) },
      splitLine: { lineStyle: { color: '#EBEEF5' } }
    },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: COLORS[i], borderRadius: [4, 4, 0, 0] }
      })),
      label: {
        show: true,
        position: 'top',
        formatter: (p) => p.value.toFixed(4),
        fontSize: 11
      },
      barWidth: '45%'
    }]
  }
}

function initChart() {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)
  const values = getValues()
  const option = props.chartType === 'bar' ? buildBar(values) : buildRadar(values)
  chartInstance.setOption({ backgroundColor: '#fff', ...option })
}

const resize = () => chartInstance?.resize()
onMounted(() => { initChart(); window.addEventListener('resize', resize) })
onUnmounted(() => { window.removeEventListener('resize', resize); chartInstance?.dispose() })
watch(() => [props.metrics, props.chartType], initChart, { deep: true })
</script>
