<template>
  <div class="keras-wrap">
    <el-empty
      v-if="!canRenderLoss && !canRenderMetric && !canRenderLr"
      description="无可绘制的训练曲线（缺少 loss / auc / lr 等序列）"
      :image-size="64"
    />
    <template v-else>
      <div v-if="canRenderLoss" ref="lossRef" :style="{ height, width: '100%' }" />
      <div
        v-if="canRenderMetric"
        ref="metricRef"
        :style="{
          height,
          width: '100%',
          marginTop: canRenderLoss ? '16px' : '0'
        }"
      />
      <div
        v-if="canRenderLr"
        ref="lrRef"
        :style="{
          height,
          width: '100%',
          marginTop: canRenderLoss || canRenderMetric ? '16px' : '0'
        }"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  /** Keras model.fit 的 history.history（已 JSON 序列化） */
  history: { type: Object, default: () => ({}) },
  /** 单个图表高度 */
  height: { type: String, default: '240px' }
})

const lossRef = ref(null)
const metricRef = ref(null)
const lrRef = ref(null)
let lossChart = null
let metricChart = null
let lrChart = null

function toNumSeries(arr) {
  if (!Array.isArray(arr)) return null
  const nums = arr.map((x) => Number(x)).filter((x) => !Number.isNaN(x))
  return nums.length ? nums : null
}

function epochLabels(n) {
  return Array.from({ length: n }, (_, i) => String(i + 1))
}

const canRenderLoss = computed(() => {
  const h = props.history || {}
  return !!(toNumSeries(h.loss)?.length || toNumSeries(h.val_loss)?.length)
})

const canRenderMetric = computed(() => {
  const h = props.history || {}
  return !!(
    toNumSeries(h.auc)?.length ||
    toNumSeries(h.val_auc)?.length ||
    toNumSeries(h.accuracy)?.length ||
    toNumSeries(h.val_accuracy)?.length
  )
})

const canRenderLr = computed(() => {
  const h = props.history || {}
  return !!toNumSeries(h.lr)?.length
})

function maxEpoch(...series) {
  return Math.max(0, ...series.map((s) => (Array.isArray(s) ? s.length : 0)))
}

function buildLossOption(h) {
  const loss = toNumSeries(h.loss)
  const valLoss = toNumSeries(h.val_loss)
  const n = maxEpoch(loss, valLoss)
  if (n === 0) return null
  const x = epochLabels(n)
  const series = []
  if (loss?.length) {
    series.push({
      name: 'loss',
      type: 'line',
      data: loss.slice(0, n),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#E6A23C', width: 2 }
    })
  }
  if (valLoss?.length) {
    series.push({
      name: 'val_loss',
      type: 'line',
      data: valLoss.slice(0, n),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#F56C6C', width: 2 }
    })
  }
  return {
    backgroundColor: '#fff',
    title: {
      text: 'Loss',
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, fontWeight: 'bold', color: '#303133' }
    },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: series.map((s) => s.name) },
    grid: { left: '10%', right: '6%', bottom: '18%', top: '18%' },
    xAxis: {
      type: 'category',
      data: x,
      name: 'Epoch',
      nameLocation: 'middle',
      nameGap: 22,
      axisLabel: { fontSize: 11 }
    },
    yAxis: { type: 'value', name: 'Loss', scale: true, splitLine: { lineStyle: { color: '#EBEEF5' } } },
    series
  }
}

function buildMetricOption(h) {
  const auc = toNumSeries(h.auc)
  const valAuc = toNumSeries(h.val_auc)
  const acc = toNumSeries(h.accuracy)
  const valAcc = toNumSeries(h.val_accuracy)
  const n = maxEpoch(auc, valAuc, acc, valAcc)
  if (n === 0) return null
  const x = epochLabels(n)
  const series = []
  const add = (name, data, color) => {
    if (!data?.length) return
    series.push({
      name,
      type: 'line',
      data: data.slice(0, n),
      smooth: true,
      showSymbol: false,
      lineStyle: { color, width: 2 }
    })
  }
  add('auc', auc, '#9B59B6')
  add('val_auc', valAuc, '#409EFF')
  add('accuracy', acc, '#67C23A')
  add('val_accuracy', valAcc, '#909399')
  if (!series.length) return null
  return {
    backgroundColor: '#fff',
    title: {
      text: 'AUC / Accuracy',
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, fontWeight: 'bold', color: '#303133' }
    },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: series.map((s) => s.name) },
    grid: { left: '10%', right: '6%', bottom: '18%', top: '18%' },
    xAxis: {
      type: 'category',
      data: x,
      name: 'Epoch',
      nameLocation: 'middle',
      nameGap: 22,
      axisLabel: { fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      name: 'Score',
      splitLine: { lineStyle: { color: '#EBEEF5' } }
    },
    series
  }
}

function buildLrOption(h) {
  const lr = toNumSeries(h.lr)
  const n = lr?.length || 0
  if (!n) return null
  const x = epochLabels(n)
  const slice = lr.slice(0, n)
  const allPos = slice.every((v) => v > 0)
  return {
    backgroundColor: '#fff',
    title: {
      text: 'Learning rate',
      left: 'center',
      top: 6,
      textStyle: { fontSize: 14, fontWeight: 'bold', color: '#303133' }
    },
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v) => (typeof v === 'number' ? v.toExponential(2) : v)
    },
    legend: { bottom: 0, data: ['lr'] },
    grid: { left: '12%', right: '6%', bottom: '18%', top: '18%' },
    xAxis: {
      type: 'category',
      data: x,
      name: 'Epoch',
      nameLocation: 'middle',
      nameGap: 22,
      axisLabel: { fontSize: 11 }
    },
    yAxis: {
      type: allPos ? 'log' : 'value',
      name: allPos ? 'LR (log)' : 'LR',
      scale: !allPos,
      splitLine: { lineStyle: { color: '#EBEEF5' } }
    },
    series: [
      {
        name: 'lr',
        type: 'line',
        data: slice,
        smooth: false,
        showSymbol: true,
        symbolSize: 5,
        lineStyle: { color: '#00A896', width: 2 },
        itemStyle: { color: '#00A896' }
      }
    ]
  }
}

function initCharts() {
  const h = props.history || {}
  nextTick(() => {
    const lossOpt = buildLossOption(h)
    const metricOpt = buildMetricOption(h)
    const lrOpt = buildLrOption(h)

    if (lossRef.value) {
      if (lossChart) lossChart.dispose()
      lossChart = null
      if (lossOpt) {
        lossChart = echarts.init(lossRef.value)
        lossChart.setOption(lossOpt)
      }
    }

    if (metricRef.value) {
      if (metricChart) metricChart.dispose()
      metricChart = null
      if (metricOpt) {
        metricChart = echarts.init(metricRef.value)
        metricChart.setOption(metricOpt)
      }
    }

    if (lrRef.value) {
      if (lrChart) lrChart.dispose()
      lrChart = null
      if (lrOpt) {
        lrChart = echarts.init(lrRef.value)
        lrChart.setOption(lrOpt)
      }
    }
  })
}

function resizeAll() {
  lossChart?.resize()
  metricChart?.resize()
  lrChart?.resize()
}

onMounted(() => {
  initCharts()
  window.addEventListener('resize', resizeAll)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeAll)
  lossChart?.dispose()
  metricChart?.dispose()
  lrChart?.dispose()
  lossChart = null
  metricChart = null
  lrChart = null
})

watch(() => props.history, initCharts, { deep: true })
watch([canRenderLoss, canRenderMetric, canRenderLr], () => initCharts())
</script>

<style scoped>
.keras-wrap {
  width: 100%;
}
</style>
