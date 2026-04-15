<template>
  <div class="history hc-page-shell">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header history-card-header">
          <el-alert
            v-if="historySource === 'server'"
            type="info"
            :closable="false"
            show-icon
            class="history-patient-alert"
            title="患者端预测历史"
            description="仅展示当前登录账号（用户 ID）在监测分析中保存的记录，与本人关联的患者档案一致；不显示其他账号或医护代录的数据。"
          />
          <div class="history-toolbar-row">
            <div class="history-card-title">
              <el-icon><Document /></el-icon>
              <span>历史记录</span>
              <el-tag type="info" effect="plain" round size="small" class="history-count-tag">
                {{ historyList.length }} 条
              </el-tag>
            </div>
            <div class="history-toolbar">
              <el-button
                type="danger"
                plain
                size="default"
                :disabled="selectedRows.length === 0 || historySource === 'server'"
                @click="handleBatchDelete"
              >
                <el-icon><Delete /></el-icon>
                批量删除 ({{ selectedRows.length }})
              </el-button>
              <el-button type="warning" plain size="default" :disabled="historySource === 'server'" @click="handleClearAll">
                <el-icon><DeleteFilled /></el-icon>
                清空全部
              </el-button>
              <el-button type="primary" size="default" @click="loadHistory">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </div>
        </div>
      </template>

      <el-table
        :data="historyList"
        class="history-table"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        stripe
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="索引" width="80" sortable>
          <template #default="scope">
            <el-tag type="info" size="small">#{{ scope.row.id }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="时间" width="180" sortable>
          <template #default="scope">
            <div>
              <div>{{ scope.row.date }}</div>
              <div style="font-size: 12px; color: #909399">
                {{ formatTimestamp(scope.row.timestamp) }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="100" />
        <el-table-column prop="gender" label="性别" width="100">
          <template #default="scope">
            {{
              scope.row.gender === 'M' || scope.row.gender === 1 || scope.row.gender === '1'
                ? '男'
                : '女'
            }}
          </template>
        </el-table-column>
        <el-table-column prop="bmi" label="BMI" width="100" />
        <el-table-column prop="riskScore" label="风险评分" width="120" sortable>
          <template #default="scope">
            <el-tag :type="getRiskType(scope.row.riskScore)">
              {{ scope.row.riskScore }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="prediction" label="预测结果" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.prediction === 1 ? 'danger' : 'success'">
              {{ scope.row.prediction === 1 ? '高风险' : '低风险' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="scope">
            {{ scope.row.confidence ? (scope.row.confidence * 100).toFixed(1) + '%' : 'N/A' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="viewDetail(scope.row)"
              plain
            >
              <el-icon><ViewIcon /></el-icon>
              查看详情
            </el-button>
            <el-button
              type="danger"
              size="small"
              :disabled="historySource === 'server'"
              @click="handleDelete(scope.row)"
              plain
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="!loading && historyList.length === 0"
        :description="
          historySource === 'server'
            ? '暂无与当前账号用户 ID 一致的预测记录；请在登录后从本人患者档案进入「监测分析」并完成评估（将写入服务端）。'
            : '在「监测分析」完成评估后会自动保存到此'
        "
        :image-size="100"
      />
    </el-card>

    <!-- 趋势分析图表 -->
    <el-card v-if="historyList.length > 0" class="hc-card-elevated history-chart-card" shadow="never">
      <template #header>
        <div class="history-chart-head">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据趋势分析</span>
        </div>
      </template>
      <div ref="trendChartRef" style="width: 100%; height: 400px; padding: 10px;"></div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="分析详情"
      width="900px"
    >
      <div v-if="currentDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="记录ID">
            <el-tag type="info">#{{ currentDetail.id }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="分析时间">
            {{ currentDetail.date }}
            <div style="font-size: 12px; color: #909399; margin-top: 4px">
              时间戳: {{ currentDetail.timestamp }}
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="年龄">{{ currentDetail.age }}</el-descriptions-item>
          <el-descriptions-item label="性别">
            {{
              currentDetail.gender === 'M' || currentDetail.gender === 1 || currentDetail.gender === '1'
                ? '男'
                : '女'
            }}
          </el-descriptions-item>
          <el-descriptions-item label="身高 (cm)">{{ currentDetail.height }}</el-descriptions-item>
          <el-descriptions-item label="体重 (kg)">{{ currentDetail.weight }}</el-descriptions-item>
          <el-descriptions-item label="BMI">{{ currentDetail.bmi?.toFixed(2) || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="使用的模型">
            {{ currentDetail.modelId || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="风险评分" :span="2">
            <el-tag :type="getRiskType(currentDetail.riskScore)" size="large">
              {{ currentDetail.riskScore }}%
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预测结果" :span="2">
            <el-tag :type="currentDetail.prediction === 1 ? 'danger' : 'success'" size="large">
              {{ currentDetail.prediction === 1 ? '高风险' : '低风险' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预测置信度">
            {{ currentDetail.confidence ? (currentDetail.confidence * 100).toFixed(2) + '%' : 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="类别0概率">
            {{ currentDetail.probability && currentDetail.probability[0] ? (currentDetail.probability[0] * 100).toFixed(2) + '%' : 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="类别1概率">
            {{ currentDetail.probability && currentDetail.probability[1] ? (currentDetail.probability[1] * 100).toFixed(2) + '%' : 'N/A' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- HRV特征 -->
        <el-divider>HRV特征</el-divider>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="平均RR间期 (ms)">
            {{ currentDetail.mean_rr || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="SDNN (ms)">
            {{ currentDetail.sdnn || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="RMSSD (ms)">
            {{ currentDetail.rmssd || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="pNN50 (%)">
            {{ currentDetail.pnn50 || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="LF/HF比值">
            {{ currentDetail.lf_hf_ratio || 'N/A' }}
          </el-descriptions-item>
        </el-descriptions>

        <template v-if="hasMeaningfulExtendedClinical(currentDetail)">
          <el-divider>体征、实验室与危险因素</el-divider>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="血压(mmHg)">
              <template
                v-if="
                  currentDetail.blood_pressure_systolic != null &&
                  currentDetail.blood_pressure_systolic !== '' ||
                  currentDetail.blood_pressure_diastolic != null &&
                  currentDetail.blood_pressure_diastolic !== ''
                "
              >
                {{ currentDetail.blood_pressure_systolic ?? '—' }} /
                {{ currentDetail.blood_pressure_diastolic ?? '—' }}
              </template>
              <template v-else>—</template>
            </el-descriptions-item>
            <el-descriptions-item label="静息心率">
              {{
                currentDetail.resting_heart_rate != null && currentDetail.resting_heart_rate !== ''
                  ? currentDetail.resting_heart_rate + ' 次/分'
                  : '—'
              }}
            </el-descriptions-item>
            <el-descriptions-item label="腰围">
              {{
                currentDetail.waist_cm != null && currentDetail.waist_cm !== ''
                  ? currentDetail.waist_cm + ' cm'
                  : '—'
              }}
            </el-descriptions-item>
            <el-descriptions-item label="吸烟">
              {{ smokeLabel(currentDetail.smoke_status) }}
            </el-descriptions-item>
            <el-descriptions-item label="总胆固醇">
              {{ labFmt(currentDetail.total_cholesterol, 'mmol/L') }}
            </el-descriptions-item>
            <el-descriptions-item label="LDL-C">
              {{ labFmt(currentDetail.ldl_cholesterol, 'mmol/L') }}
            </el-descriptions-item>
            <el-descriptions-item label="HDL-C">
              {{ labFmt(currentDetail.hdl_cholesterol, 'mmol/L') }}
            </el-descriptions-item>
            <el-descriptions-item label="甘油三酯">
              {{ labFmt(currentDetail.triglyceride, 'mmol/L') }}
            </el-descriptions-item>
            <el-descriptions-item label="空腹血糖">
              {{ labFmt(currentDetail.fasting_glucose, 'mmol/L') }}
            </el-descriptions-item>
            <el-descriptions-item label="HbA1c">
              {{ labFmt(currentDetail.hba1c, '%') }}
            </el-descriptions-item>
            <el-descriptions-item label="体力活动" :span="2">
              {{ activityLabel(currentDetail.physical_activity) }}
            </el-descriptions-item>
            <el-descriptions-item label="糖尿病">
              {{ yesNoFlag(currentDetail.diabetes) }}
            </el-descriptions-item>
            <el-descriptions-item label="高血压(诊断)">
              {{ yesNoFlag(currentDetail.hypertension_dx) }}
            </el-descriptions-item>
            <el-descriptions-item label="血脂异常">
              {{ yesNoFlag(currentDetail.dyslipidemia) }}
            </el-descriptions-item>
            <el-descriptions-item label="早发冠心病家族史">
              {{ yesNoFlag(currentDetail.family_history_cad) }}
            </el-descriptions-item>
            <el-descriptions-item label="胸痛/心绞痛症状" :span="2">
              {{ yesNoFlag(currentDetail.chest_pain_symptom) }}
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { Document, Delete, DeleteFilled, Refresh, View as ViewIcon, DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storage } from '../utils/storage'
import apiService from '../services/api'
import {
  smokeLabel,
  activityLabel,
  yesNoFlag,
  labFmt,
  hasMeaningfulExtendedClinical
} from '../utils/clinicalDisplay'
import * as echarts from 'echarts'

function parseStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

/** 将服务端预测记录转为历史表行结构（与本地 storage 字段对齐） */
function mapServerPredictionToRow(p) {
  let pPos = 0.5
  try {
    const arr = JSON.parse(p.probability || '[]')
    if (Array.isArray(arr) && arr.length > 1) pPos = Number(arr[1])
    else if (Array.isArray(arr) && arr.length === 1) pPos = Number(arr[0])
  } catch (_) {
    /* ignore */
  }
  if (!Number.isFinite(pPos)) pPos = 0.5

  let clinical = {}
  if (p.input_features) {
    try {
      const parsed = JSON.parse(p.input_features)
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        clinical = parsed
      }
    } catch (_) {
      /* ignore */
    }
  }

  const ts = p.created_at ? new Date(p.created_at).getTime() : Date.now()
  const base = {
    id: p.id,
    timestamp: ts,
    date: p.created_at
      ? new Date(p.created_at).toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
      : new Date(ts).toLocaleString('zh-CN'),
    riskScore: Math.round(pPos * 100),
    prediction: p.prediction,
    probability: [1 - pPos, pPos],
    confidence: Math.max(pPos, 1 - pPos),
    method: 'single',
    modelId: p.model_id,
    modelIds: null,
    modelCount: 1,
    features: p.input_features,
    user_id: p.user_id,
    patient_id: p.patient_id,
    _fromServer: true
  }
  return { ...clinical, ...base }
}

export default {
  name: 'History',
  components: {
    Document,
    Delete,
    DeleteFilled,
    Refresh,
    ViewIcon,
    DataAnalysis
  },
  setup() {
    const loading = ref(false)
    /** local: 浏览器本地；server: 患者账号走 API，仅本人 user_id 的记录 */
    const historySource = ref('local')
    const historyList = ref([])
    const detailVisible = ref(false)
    const currentDetail = ref(null)
    const selectedRows = ref([])
    const trendChartRef = ref(null)
    let trendChart = null

    const loadHistory = async () => {
      loading.value = true
      try {
        const user = parseStoredUser()
        if (user && user.role === 'patient') {
          historySource.value = 'server'
          const res = await apiService.getMyPatientPredictions({ skip: 0, limit: 500 })
          const inner = res.data || {}
          const items = inner.items || []
          historyList.value = items.map(mapServerPredictionToRow)
          historyList.value.sort((a, b) => {
            const timeA = a.timestamp || new Date(a.date || 0).getTime()
            const timeB = b.timestamp || new Date(b.date || 0).getTime()
            return timeB - timeA
          })
          ElMessage.success(`已加载 ${historyList.value.length} 条记录（用户 ID: ${user.id}）`)
        } else {
          historySource.value = 'local'
          historyList.value = storage.getHistory()
          historyList.value.sort((a, b) => {
            const timeA = a.timestamp || new Date(a.date || 0).getTime()
            const timeB = b.timestamp || new Date(b.date || 0).getTime()
            return timeB - timeA
          })
          ElMessage.success(`已加载 ${historyList.value.length} 条记录`)
        }
      } catch (error) {
        ElMessage.error('加载历史记录失败: ' + (error.message || '请求失败'))
      } finally {
        loading.value = false
      }
    }

    const getRiskType = (score) => {
      const numScore = parseFloat(score)
      if (numScore < 30) return 'success'
      if (numScore < 60) return 'warning'
      return 'danger'
    }

    const formatTimestamp = (timestamp) => {
      if (!timestamp) return 'N/A'
      const date = new Date(timestamp)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    const viewDetail = (row) => {
      currentDetail.value = row
      detailVisible.value = true
    }

    const handleDelete = async (row) => {
      if (historySource.value === 'server') {
        ElMessage.info('患者端预测记录保存在服务器，暂不支持在此页删除')
        return
      }
      try {
        await ElMessageBox.confirm(
          `确定要删除记录 #${row.id} 吗？`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        if (storage.deleteHistory(row.id)) {
          ElMessage.success('删除成功')
          loadHistory()
        } else {
          ElMessage.error('删除失败')
        }
      } catch (error) {
        // 用户取消
      }
    }

    const handleSelectionChange = (selection) => {
      selectedRows.value = selection
    }

    const handleBatchDelete = async () => {
      if (historySource.value === 'server') {
        ElMessage.info('患者端预测记录保存在服务器，暂不支持在此页删除')
        return
      }
      if (selectedRows.value.length === 0) {
        ElMessage.warning('请先选择要删除的记录')
        return
      }

      try {
        await ElMessageBox.confirm(
          `确定要删除选中的 ${selectedRows.value.length} 条记录吗？`,
          '确认批量删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        const ids = selectedRows.value.map(row => row.id)
        if (storage.deleteHistoryBatch(ids)) {
          ElMessage.success(`成功删除 ${ids.length} 条记录`)
          selectedRows.value = []
          loadHistory()
        } else {
          ElMessage.error('批量删除失败')
        }
      } catch (error) {
        // 用户取消
      }
    }

    const handleClearAll = async () => {
      if (historySource.value === 'server') {
        ElMessage.info('患者端预测记录保存在服务器，暂不支持在此页清空')
        return
      }
      if (historyList.value.length === 0) {
        ElMessage.warning('没有可清空的记录')
        return
      }

      try {
        await ElMessageBox.confirm(
          `确定要清空所有 ${historyList.value.length} 条记录吗？此操作不可恢复！`,
          '确认清空',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        if (storage.clearHistory()) {
          ElMessage.success('已清空所有记录')
          historyList.value = []
          selectedRows.value = []
        } else {
          ElMessage.error('清空失败')
        }
      } catch (error) {
        // 用户取消
      }
    }

    // 初始化趋势图表
    const initTrendChart = () => {
      if (!trendChartRef.value || historyList.value.length === 0) return

      if (trendChart) {
        trendChart.dispose()
      }

      trendChart = echarts.init(trendChartRef.value)

      // 准备数据 - 按时间排序
      const sortedData = [...historyList.value].sort((a, b) => {
        const timeA = a.timestamp || new Date(a.date || 0).getTime()
        const timeB = b.timestamp || new Date(b.date || 0).getTime()
        return timeA - timeB
      })

      const dates = sortedData.map(item => {
        const timestamp = item.timestamp || new Date(item.date || 0).getTime()
        const date = new Date(timestamp)
        return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
      })

      const riskScores = sortedData.map(item => parseFloat(item.riskScore) || 0)
      const predictions = sortedData.map(item => item.prediction === 1 ? 1 : 0)

      const option = {
        title: {
          text: '风险评分趋势',
          left: 'center',
          textStyle: {
            fontSize: 18,
            fontWeight: 'bold'
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: (params) => {
            let result = `<div style="padding: 5px;">
              <div style="font-weight: bold; margin-bottom: 5px;">${params[0].axisValue}</div>`
            params.forEach(param => {
              const value = param.value
              const unit = param.seriesName === '风险评分' ? '%' : ''
              const color = param.color
              result += `<div style="margin-top: 3px;">
                <span style="display: inline-block; width: 10px; height: 10px; background-color: ${color}; margin-right: 5px;"></span>
                ${param.seriesName}: <span style="color: ${color}; font-weight: bold;">${value.toFixed(1)}${unit}</span>
              </div>`
            })
            result += '</div>'
            return result
          }
        },
        legend: {
          data: ['风险评分', '预测结果'],
          top: 35
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: dates,
          axisLabel: {
            rotate: 45,
            fontSize: 11
          }
        },
        yAxis: [
          {
            type: 'value',
            name: '风险评分 (%)',
            min: 0,
            max: 100,
            position: 'left',
            axisLabel: {
              formatter: '{value}%'
            },
            splitLine: {
              show: true,
              lineStyle: {
                type: 'dashed'
              }
            }
          },
          {
            type: 'value',
            name: '预测结果',
            min: 0,
            max: 1,
            position: 'right',
            axisLabel: {
              formatter: (value) => value === 0 ? '低风险' : value === 1 ? '高风险' : ''
            }
          }
        ],
        series: [
          {
            name: '风险评分',
            type: 'line',
            smooth: true,
            data: riskScores,
            itemStyle: {
              color: '#5470c6'
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(84, 112, 198, 0.3)' },
                { offset: 1, color: 'rgba(84, 112, 198, 0.1)' }
              ])
            },
            markLine: {
              data: [
                { yAxis: 30, name: '低风险阈值', lineStyle: { color: '#67c23a', type: 'dashed' } },
                { yAxis: 60, name: '中风险阈值', lineStyle: { color: '#e6a23c', type: 'dashed' } }
              ],
              label: {
                formatter: '{b}'
              }
            }
          },
          {
            name: '预测结果',
            type: 'scatter',
            yAxisIndex: 1,
            data: predictions.map((pred, index) => [index, pred]),
            symbolSize: 8,
            itemStyle: {
              color: (params) => {
                return params.value[1] === 1 ? '#f56c6c' : '#67c23a'
              }
            }
          }
        ]
      }

      trendChart.setOption(option)

      // 响应式调整
      window.addEventListener('resize', () => {
        if (trendChart) {
          trendChart.resize()
        }
      })
    }

    // 监听历史记录变化，更新图表
    watch(
      () => historyList.value,
      () => {
        nextTick(() => {
          initTrendChart()
        })
      },
      { deep: true }
    )

    onMounted(() => {
      loadHistory()
      nextTick(() => {
        initTrendChart()
      })
    })

    onBeforeUnmount(() => {
      if (trendChart) {
        trendChart.dispose()
        trendChart = null
      }
    })

    return {
      loading,
      historySource,
      historyList,
      detailVisible,
      currentDetail,
      selectedRows,
      trendChartRef,
      getRiskType,
      formatTimestamp,
      viewDetail,
      handleDelete,
      handleSelectionChange,
      handleBatchDelete,
      handleClearAll,
      loadHistory,
      smokeLabel,
      activityLabel,
      yesNoFlag,
      labFmt,
      hasMeaningfulExtendedClinical
    }
  }
}
</script>

<style scoped>
.history-card-header {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
  width: 100%;
}

.history-card-header > .history-patient-alert {
  width: 100%;
}

.history-card-header .history-toolbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px 20px;
  width: 100%;
}

.history-card-title {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.history-card-title .el-icon {
  margin-right: 10px;
  font-size: 24px;
  color: #409eff;
}

.history-count-tag {
  margin-left: 12px;
}

.history-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.history-chart-card {
  margin-top: 22px;
}

.history-chart-head {
  display: flex;
  align-items: center;
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.history-chart-head .el-icon {
  margin-right: 10px;
  font-size: 22px;
  color: #409eff;
}

:deep(.el-card__header) {
  padding: 18px 22px;
  border-bottom: 1px solid #f0f2f5;
  background: var(--hc-fill-elevated, linear-gradient(180deg, #fafbfc 0%, #fff 100%));
}

:deep(.history-table) {
  border-radius: var(--hc-radius-md, 8px);
  overflow: hidden;
}

:deep(.history-table .el-table__inner-wrapper::before) {
  display: none;
}

:deep(.history-table th.el-table__cell) {
  background: #f5f7fa !important;
  font-weight: 600;
  color: #606266;
  font-size: 13px;
}

:deep(.history-table .el-table__row:hover > td.el-table__cell) {
  background: #f0f7ff !important;
}

:deep(.el-button) {
  border-radius: 6px;
  font-weight: 500;
}

:deep(.el-button--small) {
  padding: 8px 15px;
}

:deep(.el-tag) {
  border-radius: 4px;
  font-weight: 500;
}

:deep(.el-dialog) {
  border-radius: 12px;
}

:deep(.el-dialog__header) {
  padding: 24px 24px 20px;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfc;
}

:deep(.el-dialog__body) {
  padding: 24px;
}
</style>

