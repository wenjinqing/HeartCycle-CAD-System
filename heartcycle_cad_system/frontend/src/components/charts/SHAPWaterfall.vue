<template>
  <div class="shap-waterfall">
    <div class="chart-header">
      <h3>{{ title }}</h3>
      <div class="chart-actions">
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
  name: 'SHAPWaterfall',
  components: {
    BaseChart
  },
  props: {
    shapValues: {
      type: Array,
      required: true
    },
    featureValues: {
      type: Array,
      required: true
    },
    featureNames: {
      type: Array,
      required: true
    },
    baseValue: {
      type: Number,
      required: true
    },
    prediction: {
      type: Number,
      required: true
    },
    title: {
      type: String,
      default: 'SHAP值瀑布图'
    },
    height: {
      type: String,
      default: '500px'
    }
  },
  setup(props) {
    const chartRef = ref(null)
    const chartInstance = ref(null)

    // 计算瀑布图数据
    const waterfallData = computed(() => {
      if (!props.shapValues || props.shapValues.length === 0) {
        return []
      }

      // 组合特征名、值和SHAP值
      const features = props.shapValues.map((shap, idx) => ({
        name: props.featureNames[idx] || `特征${idx + 1}`,
        value: props.featureValues[idx],
        shap: shap,
        absShap: Math.abs(shap)
      }))

      // 按绝对SHAP值降序排序
      features.sort((a, b) => b.absShap - a.absShap)

      // 只显示前15个最重要的特征
      const topFeatures = features.slice(0, 15)

      // 构建瀑布图数据
      let cumulative = props.baseValue
      const data = []

      // 基础值
      data.push({
        name: `基础值\n${props.baseValue.toFixed(3)}`,
        value: props.baseValue,
        itemStyle: { color: '#999' }
      })

      // 每个特征的贡献
      topFeatures.forEach(feature => {
        cumulative += feature.shap

        data.push({
          name: `${feature.name}\n=${feature.value.toFixed(2)}`,
          value: feature.shap,
          itemStyle: {
            color: feature.shap > 0 ? '#ee6666' : '#5470c6'
          },
          tooltip: {
            formatter: () => {
              return `${feature.name}<br/>` +
                     `特征值: ${feature.value.toFixed(3)}<br/>` +
                     `SHAP值: ${feature.shap > 0 ? '+' : ''}${feature.shap.toFixed(3)}<br/>` +
                     `累积: ${cumulative.toFixed(3)}`
            }
          }
        })
      })

      // 预测值
      data.push({
        name: `预测值\n${props.prediction.toFixed(3)}`,
        value: props.prediction,
        itemStyle: { color: '#91cc75' }
      })

      return data
    })

    // 图表配置
    const chartOption = computed(() => ({
      title: {
        text: '',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        axisPointer: {
          type: 'shadow'
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
        type: 'category',
        data: waterfallData.value.map(d => d.name),
        axisLabel: {
          interval: 0,
          rotate: 45,
          fontSize: 10
        }
      },
      yAxis: {
        type: 'value',
        name: 'SHAP值',
        axisLabel: {
          formatter: '{value}'
        }
      },
      series: [
        {
          name: 'SHAP贡献',
          type: 'bar',
          data: waterfallData.value,
          label: {
            show: true,
            position: 'top',
            formatter: (params) => {
              if (params.dataIndex === 0 || params.dataIndex === waterfallData.value.length - 1) {
                return ''
              }
              return params.value > 0 ? `+${params.value.toFixed(3)}` : params.value.toFixed(3)
            },
            fontSize: 10
          },
          emphasis: {
            focus: 'series'
          }
        }
      ]
    }))

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
        link.download = 'shap_waterfall.png'
        link.click()
      }
    }

    return {
      chartRef,
      chartOption,
      onChartReady,
      exportChart
    }
  }
}
</script>

<style scoped>
.shap-waterfall {
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
