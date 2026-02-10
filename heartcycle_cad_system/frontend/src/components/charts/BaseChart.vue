<template>
  <div ref="chartRef" :style="{ width: width, height: height }"></div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'BaseChart',
  props: {
    option: {
      type: Object,
      required: true
    },
    width: {
      type: String,
      default: '100%'
    },
    height: {
      type: String,
      default: '400px'
    },
    theme: {
      type: String,
      default: null
    },
    autoResize: {
      type: Boolean,
      default: true
    }
  },
  emits: ['chart-ready', 'chart-click'],
  setup(props, { emit }) {
    const chartRef = ref(null)
    let chartInstance = null
    let resizeObserver = null

    // 初始化图表
    const initChart = () => {
      if (!chartRef.value) return

      // 如果已存在实例，先销毁
      if (chartInstance) {
        chartInstance.dispose()
      }

      // 创建新实例
      chartInstance = echarts.init(chartRef.value, props.theme)
      chartInstance.setOption(props.option)

      // 绑定点击事件
      chartInstance.on('click', (params) => {
        emit('chart-click', params)
      })

      emit('chart-ready', chartInstance)
    }

    // 更新图表配置
    const updateChart = () => {
      if (chartInstance) {
        chartInstance.setOption(props.option, true)
      }
    }

    // 调整图表大小
    const resizeChart = () => {
      if (chartInstance) {
        chartInstance.resize()
      }
    }

    // 监听配置变化
    watch(() => props.option, () => {
      nextTick(() => {
        updateChart()
      })
    }, { deep: true })

    // 监听主题变化
    watch(() => props.theme, () => {
      nextTick(() => {
        initChart()
      })
    })

    onMounted(() => {
      initChart()

      // 自动调整大小
      if (props.autoResize) {
        // 使用ResizeObserver监听容器大小变化
        resizeObserver = new ResizeObserver(() => {
          resizeChart()
        })
        resizeObserver.observe(chartRef.value)

        // 监听窗口大小变化
        window.addEventListener('resize', resizeChart)
      }
    })

    onBeforeUnmount(() => {
      // 清理资源
      if (resizeObserver) {
        resizeObserver.disconnect()
      }
      window.removeEventListener('resize', resizeChart)

      if (chartInstance) {
        chartInstance.dispose()
        chartInstance = null
      }
    })

    // 暴露方法给父组件
    const getChartInstance = () => chartInstance

    return {
      chartRef,
      getChartInstance,
      resizeChart
    }
  }
}
</script>

<style scoped>
/* 确保图表容器有明确的尺寸 */
div {
  min-height: 200px;
}
</style>
