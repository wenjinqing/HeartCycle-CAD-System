<template>
  <div class="feature-importance">
    <div class="chart-header">
      <h3>{{ title }}</h3>
      <div class="chart-actions">
        <el-button size="small" @click="toggleSort">
          {{ sortByValue ? '按名称排序' : '按重要性排序' }}
        </el-button>
        <el-button size="small" @click="exportChart">导出图表</el-button>
      </div>
    </div>
    <BaseChart
      ref="chartRef"
      :option="chartOption"
      :height="height"
      @chart-ready="onChartReady"
    />
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import BaseChart from './BaseChart.vue'

export default {
  name: 'FeatureImportanceChart',
  components: {
    BaseChart
  },
  props: {
    featureImportance: {
      type: Object,
      required: true
    },
    title: {
      type: String,
      default: '特征重要性'
    },
    height: {
      type: String,
      default: '600px'
    },
    maxFeatures: {
      type: Number,
      default: 20
    }
  },
  setup(props) {
    const chartRef = ref(null)
    const chartInstance = ref(null)
    const sortByValue = ref(true)

    // 处理特征重要性数据
    const processedData = computed(() => {
      if (!props.featureImportance || Object.keys(props.featureImportance).length === 0) {
        return { names: [], values: [] }
      }

      // 转换为数组并排序
      let features = Object.entries(props.featureImportance).map(([name, value]) => ({
        name,
        value: Math.abs(value)
      }))

      if (sortByValue.value) {
        // 按重要性降序排序
        features.sort((a, b) => b.value - a.value)
      } else {
        // 按名称排序
        features.sort((a, b) => a.name.localeCompare(b.name))
      }

      // 只取前N个特征
      features = features.slice(0, props.maxFeatures)

      return {
        names: features.map(f => f.name),
        values: features.map(f => f.value)
      }
    })

    // 图表配置
    const chartOption = computed(() => ({
      title: {
        text: '',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: (params) => {
          const param = params[0]
          return `${param.name}<br/>重要性: ${param.value.toFixed(4)}`
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        name: '平均|SHAP值|',
        axisLabel: {
          formatter: '{value}'
        }
      },
      yAxis: {
        type: 'category',
        data: processedData.value.names,
        axisLabel: {
          fontSize: 11
        },
        inverse: true  // 最重要的特征在顶部
      },
      series: [
        {
          name: '特征重要性',
          type: 'bar',
          data: processedData.value.values.map((value, idx) => ({
            value,
            itemStyle: {
              color: getColorByIndex(idx, processedData.value.values.length)
            }
          })),
          label: {
            show: true,
            position: 'right',
            formatter: '{c}',
            fontSize: 10
          },
          emphasis: {
            focus: 'series'
          },
          barMaxWidth: 30
        }
      ]
    }))

    // 根据索引获取颜色（渐变色）
    const getColorByIndex = (index, total) => {
      const ratio = index / Math.max(total - 1, 1)
      // 从红色渐变到蓝色
      const r = Math.round(238 - (238 - 84) * ratio)
      const g = Math.round(102 + (112 - 102) * ratio)
      const b = Math.round(102 + (198 - 102) * ratio)
      return `rgb(${r}, ${g}, ${b})`
    }

    // 切换排序方式
    const toggleSort = () => {
      sortByValue.value = !sortByValue.value
    }

    // 图表就绪回调
    const onChartReady = (instance) => {
      chartInstance.value = instance
    }

    // 导出图表
    const exportChart = () => {
      if (chartInstance.value) {
        const url = chartInstance.value.getDataURL({
          type: 'png',
          pixelRatio: 2,
          backgroundColor: '#fff'
        })

        const link = document.createElement('a')
        link.href = url
        link.download = 'feature_importance.png'
        link.click()
      }
    }

    return {
      chartRef,
      chartOption,
      sortByValue,
      toggleSort,
      onChartReady,
      exportChart
    }
  }
}
</script>

<style scoped>
.feature-importance {
  width: 100%;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.chart-actions {
  display: flex;
  gap: 8px;
}
</style>
