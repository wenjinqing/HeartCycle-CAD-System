<template>
  <div ref="chartRef" :style="{ height, width: '100%' }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  originalDistribution: { type: Object, default: () => ({}) },
  resampledDistribution: { type: Object, default: () => ({}) },
  smoteApplied: { type: Boolean, default: false },
  height: { type: String, default: '360px' }
})

const chartRef = ref(null)
let chartInstance = null

function initChart() {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const origKeys = Object.keys(props.originalDistribution)
  const classes = origKeys.length ? origKeys : ['0', '1']
  const classLabels = classes.map(c => c === '0' ? '低风险 (Class 0)' : c === '1' ? '高风险 (Class 1)' : `Class ${c}`)

  const origValues = classes.map(c => props.originalDistribution[c] ?? 0)
  const resampledValues = classes.map(c => props.resampledDistribution[c] ?? 0)

  const series = [
    {
      name: '原始数据',
      type: 'bar',
      data: origValues,
      barWidth: props.smoteApplied ? '30%' : '40%',
      itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] },
      label: {
        show: true, position: 'top',
        formatter: (p) => `${p.value}\n(${((p.value / origValues.reduce((a, b) => a + b, 0)) * 100).toFixed(1)}%)`
      }
    }
  ]

  if (props.smoteApplied) {
    series.push({
      name: 'SMOTE后',
      type: 'bar',
      data: resampledValues,
      barWidth: '30%',
      itemStyle: { color: '#67C23A', borderRadius: [4, 4, 0, 0] },
      label: {
        show: true, position: 'top',
        formatter: (p) => `${p.value}\n(${((p.value / resampledValues.reduce((a, b) => a + b, 0)) * 100).toFixed(1)}%)`
      }
    })
  }

  const option = {
    backgroundColor: '#fff',
    title: {
      text: '类别分布' + (props.smoteApplied ? ' (SMOTE前后对比)' : ''),
      left: 'center', top: 8,
      textStyle: { fontSize: 15, fontWeight: 'bold', color: '#303133' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        let html = `<b>${params[0].axisValue}</b><br/>`
        params.forEach(p => {
          html += `${p.marker}${p.seriesName}: <b>${p.value}</b><br/>`
        })
        return html
      }
    },
    legend: props.smoteApplied
      ? { data: ['原始数据', 'SMOTE后'], bottom: 4, textStyle: { fontSize: 12 } }
      : { show: false },
    grid: { left: '10%', right: '5%', bottom: props.smoteApplied ? '14%' : '10%', top: '18%' },
    xAxis: {
      type: 'category',
      data: classLabels,
      axisLabel: { fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      name: '样本数量',
      nameTextStyle: { fontSize: 12 },
      splitLine: { lineStyle: { color: '#EBEEF5' } }
    },
    series
  }
  chartInstance.setOption(option)
}

const resize = () => chartInstance?.resize()
onMounted(() => { initChart(); window.addEventListener('resize', resize) })
onUnmounted(() => { window.removeEventListener('resize', resize); chartInstance?.dispose() })
watch(() => [props.originalDistribution, props.resampledDistribution, props.smoteApplied], initChart, { deep: true })
</script>
