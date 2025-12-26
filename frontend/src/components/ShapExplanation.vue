<template>
  <div class="shap-explanation">
    <el-card v-if="globalImportance" class="shap-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>全局特征重要性</span>
          <el-tag type="info" size="small">模型整体解释</el-tag>
        </div>
      </template>
      <div ref="globalChartRef" class="chart-container" style="height: 400px;"></div>
    </el-card>

    <el-card v-if="shapData" class="shap-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>单样本预测解释</span>
          <el-tag :type="shapData.prediction === 1 ? 'danger' : 'success'" size="small">
            {{ shapData.prediction === 1 ? '高风险' : '低风险' }}
          </el-tag>
        </div>
      </template>
      
      <div v-if="shapData.prediction !== undefined" class="prediction-info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="预测结果">
            <el-tag :type="shapData.prediction === 1 ? 'danger' : 'success'">
              {{ shapData.prediction === 1 ? '高风险 (1)' : '低风险 (0)' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            {{ (shapData.probability[shapData.prediction] * 100).toFixed(2) }}%
          </el-descriptions-item>
          <el-descriptions-item label="基础值" :span="2">
            {{ shapData.base_value.toFixed(4) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div ref="instanceChartRef" class="chart-container" style="height: 400px; margin-top: 20px;"></div>

      <el-table
        :data="shapTableData"
        stripe
        border
        style="margin-top: 20px"
        :max-height="400"
      >
        <el-table-column prop="feature" label="特征名称" width="200" show-overflow-tooltip />
        <el-table-column prop="value" label="特征值" width="120">
          <template #default="{ row }">
            {{ row.value.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="shapValue" label="SHAP值" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.shapValue >= 0 ? '#f56c6c' : '#67c23a' }">
              {{ row.shapValue >= 0 ? '+' : '' }}{{ row.shapValue.toFixed(4) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="contribution" label="贡献方向" width="120">
          <template #default="{ row }">
            <el-tag :type="row.shapValue >= 0 ? 'danger' : 'success'" size="small">
              {{ row.shapValue >= 0 ? '推高风险' : '降低风险' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="absShap" label="重要性" width="120" sortable>
          <template #default="{ row }">
            {{ row.absShap.toFixed(4) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-empty v-if="!globalImportance && !shapData" description="暂无SHAP解释数据" />
  </div>
</template>

<script>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'ShapExplanation',
  props: {
    globalImportance: {
      type: Object,
      default: null
    },
    shapData: {
      type: Object,
      default: null
    }
  },
  setup(props) {
    const globalChartRef = ref(null)
    const instanceChartRef = ref(null)
    let globalChart = null
    let instanceChart = null

    const shapTableData = ref([])

    // 初始化全局重要性图表
    const initGlobalChart = () => {
      if (!globalChartRef.value || !props.globalImportance) return

      if (globalChart) {
        globalChart.dispose()
      }

      globalChart = echarts.init(globalChartRef.value)

      const featureRanking = props.globalImportance.feature_ranking || []
      const features = featureRanking.map(item => item.feature)
      const importances = featureRanking.map(item => item.importance)

      const option = {
        title: {
          text: '特征重要性排序',
          left: 'center',
          textStyle: {
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          },
          formatter: (params) => {
            const data = params[0]
            return `${data.name}<br/>重要性: ${data.value.toFixed(4)}`
          }
        },
        grid: {
          left: '15%',
          right: '10%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'value',
          name: '平均绝对SHAP值',
          nameLocation: 'middle',
          nameGap: 30
        },
        yAxis: {
          type: 'category',
          data: features,
          axisLabel: {
            interval: 0,
            rotate: 0,
            formatter: (value) => {
              // 如果特征名太长，截断
              return value.length > 15 ? value.substring(0, 15) + '...' : value
            }
          }
        },
        series: [
          {
            name: '特征重要性',
            type: 'bar',
            data: importances,
            itemStyle: {
              color: () => {
                // 渐变色设置
                return echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#91cc75' },
                  { offset: 1, color: '#5470c6' }
                ])
              }
            },
            label: {
              show: true,
              position: 'right',
              formatter: (params) => {
                return params.value.toFixed(4)
              }
            }
          }
        ]
      }

      globalChart.setOption(option)

      // 响应式调整
      window.addEventListener('resize', () => {
        if (globalChart) {
          globalChart.resize()
        }
      })
    }

    // 初始化单样本解释图表（瀑布图）
    const initInstanceChart = () => {
      if (!instanceChartRef.value || !props.shapData) return

      if (instanceChart) {
        instanceChart.dispose()
      }

      instanceChart = echarts.init(instanceChartRef.value)

      const { shap_values, feature_names, base_value } = props.shapData
      
      // 按SHAP值绝对值排序
      const dataWithNames = feature_names.map((name, idx) => ({
        name,
        value: shap_values[idx],
        absValue: Math.abs(shap_values[idx])
      })).sort((a, b) => b.absValue - a.absValue)

      const sortedNames = dataWithNames.map(item => item.name)
      const sortedValues = dataWithNames.map(item => item.value)

      // 计算累积值（用于瀑布图）
      const cumulativeValues = [base_value]
      sortedValues.forEach(val => {
        cumulativeValues.push(cumulativeValues[cumulativeValues.length - 1] + val)
      })

      // 构建瀑布图数据
      const waterfallData = sortedValues.map((val) => ({
        value: val,
        itemStyle: {
          color: val >= 0 ? '#f56c6c' : '#67c23a'
        }
      }))

      const option = {
        title: {
          text: '特征贡献瀑布图',
          left: 'center',
          textStyle: {
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          },
          formatter: (params) => {
            const dataIndex = params[0].dataIndex
            const name = sortedNames[dataIndex]
            const value = sortedValues[dataIndex]
            const cumulative = cumulativeValues[dataIndex + 1]
            return `${name}<br/>SHAP值: ${value >= 0 ? '+' : ''}${value.toFixed(4)}<br/>累积值: ${cumulative.toFixed(4)}`
          }
        },
        grid: {
          left: '15%',
          right: '10%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: sortedNames,
          axisLabel: {
            interval: 0,
            rotate: 45,
            formatter: (value) => {
              return value.length > 10 ? value.substring(0, 10) + '...' : value
            }
          }
        },
        yAxis: {
          type: 'value',
          name: 'SHAP值',
          nameLocation: 'middle',
          nameGap: 50
        },
        series: [
          {
            name: '特征贡献',
            type: 'bar',
            data: waterfallData,
            label: {
              show: true,
              position: 'inside',
              formatter: (params) => {
                const val = params.value
                return val >= 0 ? `+${val.toFixed(3)}` : val.toFixed(3)
              },
              color: '#fff'
            },
            markLine: {
              data: [
                {
                  name: '基础值',
                  yAxis: base_value,
                  lineStyle: {
                    color: '#909399',
                    type: 'dashed'
                  },
                  label: {
                    formatter: `基础值: ${base_value.toFixed(4)}`
                  }
                }
              ]
            }
          }
        ],
        legend: {
          show: false
        }
      }

      instanceChart.setOption(option)

      // 响应式调整
      window.addEventListener('resize', () => {
        if (instanceChart) {
          instanceChart.resize()
        }
      })
    }

    // 更新表格数据
    const updateTableData = () => {
      if (!props.shapData) {
        shapTableData.value = []
        return
      }

      const { shap_values, feature_names, feature_values } = props.shapData

      shapTableData.value = feature_names.map((name, idx) => ({
        feature: name,
        value: feature_values[idx],
        shapValue: shap_values[idx],
        absShap: Math.abs(shap_values[idx])
      })).sort((a, b) => b.absShap - a.absShap)
    }

    // 监听props变化
    watch(
      () => props.globalImportance,
      () => {
        nextTick(() => {
          initGlobalChart()
        })
      },
      { deep: true, immediate: true }
    )

    watch(
      () => props.shapData,
      () => {
        updateTableData()
        nextTick(() => {
          initInstanceChart()
        })
      },
      { deep: true, immediate: true }
    )

    onMounted(() => {
      nextTick(() => {
        initGlobalChart()
        initInstanceChart()
        updateTableData()
      })
    })

    onBeforeUnmount(() => {
      if (globalChart) {
        globalChart.dispose()
        globalChart = null
      }
      if (instanceChart) {
        instanceChart.dispose()
        instanceChart = null
      }
    })

    return {
      globalChartRef,
      instanceChartRef,
      shapTableData
    }
  }
}
</script>

<style scoped>
.shap-explanation {
  width: 100%;
}

.shap-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  width: 100%;
}

.prediction-info {
  margin-bottom: 20px;
}

:deep(.el-table) {
  font-size: 13px;
}
</style>

