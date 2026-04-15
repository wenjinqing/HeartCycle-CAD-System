<template>
  <div class="patient-detail hc-page-shell">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="text-large font-600 mr-3">患者详情</span>
      </template>
    </el-page-header>

    <div v-loading="loading" style="margin-top: 20px">
      <!-- 基本信息 -->
      <el-card class="info-card hc-card-elevated" shadow="never">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-button
              v-if="canEdit"
              type="primary"
              size="small"
              @click="router.push(`/patients`)"
            >
              编辑
            </el-button>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="患者编号">
            {{ patient.patient_no }}
          </el-descriptions-item>
          <el-descriptions-item label="姓名">
            {{ patient.name }}
          </el-descriptions-item>
          <el-descriptions-item label="性别">
            {{ patient.gender === 'male' ? '男' : '女' }}
          </el-descriptions-item>
          <el-descriptions-item label="年龄">
            {{ patient.age }} 岁
          </el-descriptions-item>
          <el-descriptions-item label="出生日期">
            {{ patient.birth_date || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="手机号">
            <span>{{ patientPhoneDisplay }}</span>
            <el-button
              v-if="patient.phone"
              type="primary"
              link
              size="small"
              class="phone-toggle"
              @click="showFullPhone = !showFullPhone"
            >
              {{ showFullPhone ? '隐藏' : '显示' }}
            </el-button>
          </el-descriptions-item>
          <el-descriptions-item label="职业">
            {{ patient.occupation || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="身高 / 体重">
            <template v-if="patient.height_cm || patient.weight_kg">
              {{ patient.height_cm != null ? patient.height_cm + ' cm' : '-' }}
              /
              {{ patient.weight_kg != null ? patient.weight_kg + ' kg' : '-' }}
            </template>
            <template v-else>-</template>
          </el-descriptions-item>
          <el-descriptions-item label="血压(mmHg)">
            <template
              v-if="patient.blood_pressure_systolic != null || patient.blood_pressure_diastolic != null"
            >
              {{ patient.blood_pressure_systolic ?? '-' }} /
              {{ patient.blood_pressure_diastolic ?? '-' }}
            </template>
            <template v-else>-</template>
          </el-descriptions-item>
          <el-descriptions-item label="静息心率">
            {{ patient.resting_heart_rate != null ? patient.resting_heart_rate + ' 次/分' : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="HRV(平均RR/SDNN)" :span="2">
            <template v-if="patient.hrv_mean_rr != null || patient.hrv_sdnn != null">
              平均RR: {{ patient.hrv_mean_rr ?? '-' }} ms；SDNN: {{ patient.hrv_sdnn ?? '-' }}；RMSSD:
              {{ patient.hrv_rmssd ?? '-' }}；pNN50: {{ patient.hrv_pnn50 ?? '-' }}；LF/HF:
              {{ patient.hrv_lf_hf_ratio ?? '-' }}
            </template>
            <template v-else>-</template>
          </el-descriptions-item>
          <el-descriptions-item label="主治医生（建档）">
            {{ patient.doctor_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="已绑定医生 ID">
            {{
              patient.bound_doctor_ids && patient.bound_doctor_ids.length
                ? patient.bound_doctor_ids.join('、')
                : '-'
            }}
          </el-descriptions-item>
          <el-descriptions-item label="地址" :span="2">
            {{ patient.address || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="紧急联系人">
            {{ patient.emergency_contact || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="紧急联系电话">
            {{ patient.emergency_phone || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="病史" :span="2">
            {{ patient.medical_history || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="过敏史" :span="2">
            {{ patient.allergies || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">
            {{ patient.notes || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(patient.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDate(patient.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="info-card hc-card-elevated" shadow="never" v-if="showBindingsCard">
        <template #header>
          <div class="card-header">
            <span>病历可访问医生（多对多绑定）</span>
          </div>
        </template>
        <p class="bindings-hint">
          仅下列已绑定医生可查看本患者病历；管理员/科研人员可代为绑定其他医生；已绑定医生可为团队增加同事。
        </p>
        <el-table :data="boundDoctors" stripe size="small" style="width: 100%">
          <el-table-column prop="doctor_id" label="用户 ID" width="100" />
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="full_name" label="姓名" />
          <el-table-column prop="role" label="角色" width="100" />
          <el-table-column prop="created_at" label="绑定时间" width="180" />
          <el-table-column v-if="canManageBindings" label="操作" width="100">
            <template #default="{ row }">
              <el-button
                v-if="canUnbindDoctor(row.doctor_id)"
                type="danger"
                link
                size="small"
                @click="unbindDoctor(row.doctor_id)"
              >
                解除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="canManageBindings" class="bindings-actions">
          <el-input-number
            v-model="bindDoctorIdInput"
            :min="1"
            :step="1"
            controls-position="right"
            placeholder="医生用户 ID"
            style="width: 200px"
          />
          <el-button type="primary" :loading="bindingLoading" @click="bindDoctor">绑定医生</el-button>
        </div>
      </el-card>

      <el-card class="info-card hc-card-elevated" shadow="never">
        <template #header>
          <span>实验室检查与危险因素</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="腰围">
            {{ patient.waist_cm != null ? patient.waist_cm + ' cm' : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="吸烟">
            {{ smokeLabel(patient.smoke_status) }}
          </el-descriptions-item>
          <el-descriptions-item label="总胆固醇">
            {{ labFmt(patient.total_cholesterol, 'mmol/L') }}
          </el-descriptions-item>
          <el-descriptions-item label="LDL-C">
            {{ labFmt(patient.ldl_cholesterol, 'mmol/L') }}
          </el-descriptions-item>
          <el-descriptions-item label="HDL-C">
            {{ labFmt(patient.hdl_cholesterol, 'mmol/L') }}
          </el-descriptions-item>
          <el-descriptions-item label="甘油三酯">
            {{ labFmt(patient.triglyceride, 'mmol/L') }}
          </el-descriptions-item>
          <el-descriptions-item label="空腹血糖">
            {{ labFmt(patient.fasting_glucose, 'mmol/L') }}
          </el-descriptions-item>
          <el-descriptions-item label="HbA1c">
            {{ labFmt(patient.hba1c, '%') }}
          </el-descriptions-item>
          <el-descriptions-item label="体力活动" :span="2">
            {{ activityLabel(patient.physical_activity) }}
          </el-descriptions-item>
          <el-descriptions-item label="糖尿病">
            {{ yesNoFlag(patient.diabetes) }}
          </el-descriptions-item>
          <el-descriptions-item label="高血压(诊断)">
            {{ yesNoFlag(patient.hypertension_dx) }}
          </el-descriptions-item>
          <el-descriptions-item label="血脂异常">
            {{ yesNoFlag(patient.dyslipidemia) }}
          </el-descriptions-item>
          <el-descriptions-item label="早发冠心病家族史">
            {{ yesNoFlag(patient.family_history_cad) }}
          </el-descriptions-item>
          <el-descriptions-item label="胸痛/心绞痛症状" :span="2">
            {{ yesNoFlag(patient.chest_pain_symptom) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 统计信息 -->
      <el-card class="info-card hc-card-elevated" shadow="never" v-if="statistics">
        <template #header>
          <span>统计信息</span>
        </template>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="预测总次数" :value="statistics.prediction_statistics.total_predictions" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="高风险次数" :value="statistics.prediction_statistics.high_risk_count">
              <template #suffix>
                <span style="color: #f56c6c">次</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="6">
            <el-statistic title="中风险次数" :value="statistics.prediction_statistics.medium_risk_count">
              <template #suffix>
                <span style="color: #e6a23c">次</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="6">
            <el-statistic title="低风险次数" :value="statistics.prediction_statistics.low_risk_count">
              <template #suffix>
                <span style="color: #67c23a">次</span>
              </template>
            </el-statistic>
          </el-col>
        </el-row>

        <!-- 最近一次预测 -->
        <el-divider />
        <div v-if="statistics.latest_prediction">
          <h4>最近一次预测</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="预测结果">
              {{ statistics.latest_prediction.prediction === 1 ? '有风险' : '无风险' }}
            </el-descriptions-item>
            <el-descriptions-item label="风险等级">
              <el-tag
                :type="getRiskLevelType(statistics.latest_prediction.risk_level)"
              >
                {{ getRiskLevelText(statistics.latest_prediction.risk_level) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="概率">
              {{ statistics.latest_prediction.probability }}
            </el-descriptions-item>
            <el-descriptions-item label="预测时间">
              {{ formatDate(statistics.latest_prediction.created_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 风险趋势图 -->
        <el-divider />
        <div v-if="statistics.risk_trend && statistics.risk_trend.length > 0">
          <h4>风险趋势（最近10次）</h4>
          <div ref="chartRef" style="width: 100%; height: 300px"></div>
        </div>
      </el-card>

      <!-- 预测记录 -->
      <el-card class="info-card hc-card-elevated" shadow="never">
        <template #header>
          <div class="card-header">
            <span>预测记录</span>
            <el-button
              type="primary"
              size="small"
              @click="router.push(`/monitor?patient_id=${patientId}`)"
            >
              新建预测
            </el-button>
          </div>
        </template>

        <el-table :data="predictions" stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="model_id" label="模型" width="150" />
          <el-table-column label="预测结果" width="120">
            <template #default="{ row }">
              {{ row.prediction === 1 ? '有风险' : '无风险' }}
            </template>
          </el-table-column>
          <el-table-column label="风险等级" width="120">
            <template #default="{ row }">
              <el-tag :type="getRiskLevelType(row.risk_level)">
                {{ getRiskLevelText(row.risk_level) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="probability" label="概率" width="100" />
          <el-table-column prop="doctor_notes" label="医生备注" min-width="200" />
          <el-table-column prop="created_at" label="预测时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="canEdit"
                type="primary"
                size="small"
                @click="editNotes(row)"
                link
              >
                编辑备注
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="predictionPage"
          v-model:page-size="predictionPageSize"
          :total="predictionTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadPredictions"
          @current-change="loadPredictions"
          style="margin-top: 20px; justify-content: center"
        />
      </el-card>
    </div>

    <!-- 编辑备注对话框 -->
    <el-dialog v-model="showNotesDialog" title="编辑医生备注" width="500px">
      <el-input
        v-model="editingNotes"
        type="textarea"
        :rows="5"
        placeholder="请输入医生备注"
      />
      <template #footer>
        <el-button @click="showNotesDialog = false">取消</el-button>
        <el-button type="primary" @click="submitNotes" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { api } from '@/services/api'
import { smokeLabel, activityLabel, yesNoFlag, labFmt } from '@/utils/clinicalDisplay'
import { maskPhone } from '@/utils/phonePrivacy'

const router = useRouter()
const route = useRoute()
const patientId = computed(() => route.params.id)

// 用户角色
const userRole = computed(() => {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  return user.role || 'patient'
})

const currentUserId = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem('user') || '{}')
    return u.id
  } catch {
    return null
  }
})

const canEdit = computed(() => {
  if (userRole.value === 'admin' || userRole.value === 'researcher') return true
  if (userRole.value === 'doctor') {
    const ids = patient.value.bound_doctor_ids || []
    return ids.includes(currentUserId.value)
  }
  return false
})

const showBindingsCard = computed(() =>
  ['admin', 'doctor', 'researcher', 'patient'].includes(userRole.value)
)

const canManageBindings = computed(() => {
  if (userRole.value === 'admin' || userRole.value === 'researcher') return true
  if (userRole.value === 'doctor') {
    const ids = patient.value.bound_doctor_ids || []
    return ids.includes(currentUserId.value)
  }
  return false
})

const canUnbindDoctor = (doctorId) => {
  if (userRole.value === 'admin' || userRole.value === 'researcher') return true
  if (userRole.value === 'doctor' && doctorId === currentUserId.value) return true
  return false
}

// 数据
const loading = ref(false)
const patient = ref({})
const statistics = ref(null)
const predictions = ref([])
const predictionPage = ref(1)
const predictionPageSize = ref(10)
const predictionTotal = ref(0)

// 备注编辑
const showNotesDialog = ref(false)
const editingPrediction = ref(null)
const editingNotes = ref('')
const submitting = ref(false)
const showFullPhone = ref(false)
const boundDoctors = ref([])
const bindDoctorIdInput = ref(null)
const bindingLoading = ref(false)

const patientPhoneDisplay = computed(() => {
  const p = patient.value?.phone
  if (!p) return '-'
  return showFullPhone.value ? p : maskPhone(p)
})

// 图表
const chartRef = ref(null)
let chartInstance = null

// 加载患者信息（拦截器已返回 API 体 { success, data }）
const loadBindings = async () => {
  try {
    const res = await api.get(`/patients/${patientId.value}/bindings/doctors`)
    if (res?.success && res.data?.items) {
      boundDoctors.value = res.data.items
    } else {
      boundDoctors.value = []
    }
  } catch {
    boundDoctors.value = []
  }
}

const bindDoctor = async () => {
  const id = bindDoctorIdInput.value
  if (id == null || id < 1) {
    ElMessage.warning('请输入有效的医生用户 ID')
    return
  }
  bindingLoading.value = true
  try {
    await api.post(`/patients/${patientId.value}/bindings/doctors`, { doctor_id: id })
    ElMessage.success('绑定成功')
    bindDoctorIdInput.value = null
    await loadPatient()
    await loadBindings()
  } catch (error) {
    ElMessage.error('绑定失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    bindingLoading.value = false
  }
}

const unbindDoctor = async (doctorId) => {
  try {
    await api.delete(`/patients/${patientId.value}/bindings/doctors/${doctorId}`)
    ElMessage.success('已解除绑定')
    await loadPatient()
    await loadBindings()
  } catch (error) {
    ElMessage.error('解除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const loadPatient = async () => {
  loading.value = true
  showFullPhone.value = false
  try {
    const res = await api.get(`/patients/${patientId.value}`)
    if (res?.success && res.data) {
      patient.value = res.data
      await loadBindings()
    }
  } catch (error) {
    ElMessage.error('加载患者信息失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 加载统计信息
const loadStatistics = async () => {
  try {
    const res = await api.get(`/patients/${patientId.value}/statistics`)
    if (res?.success) {
      statistics.value = res.data
      await nextTick()
      renderChart()
    }
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 加载预测记录
const loadPredictions = async () => {
  try {
    const params = {
      skip: (predictionPage.value - 1) * predictionPageSize.value,
      limit: predictionPageSize.value
    }
    const res = await api.get(`/patients/${patientId.value}/predictions`, { params })
    if (res?.success && res.data) {
      predictions.value = res.data.items || []
      predictionTotal.value = res.data.total ?? 0
    }
  } catch (error) {
    ElMessage.error('加载预测记录失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 编辑备注
const editNotes = (prediction) => {
  editingPrediction.value = prediction
  editingNotes.value = prediction.doctor_notes || ''
  showNotesDialog.value = true
}

// 提交备注
const submitNotes = async () => {
  submitting.value = true
  try {
    await api.put(`/patients/predictions/${editingPrediction.value.id}/notes`, null, {
      params: { doctor_notes: editingNotes.value }
    })
    ElMessage.success('备注已更新')
    showNotesDialog.value = false
    loadPredictions()
  } catch (error) {
    ElMessage.error('更新备注失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

// 渲染图表
const renderChart = () => {
  if (!chartRef.value || !statistics.value?.risk_trend) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  const dates = statistics.value.risk_trend.map(item => item.date)
  const probabilities = statistics.value.risk_trend.map(item => parseFloat(item.probability))

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '风险概率',
      min: 0,
      max: 1,
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: [
      {
        name: '风险概率',
        type: 'line',
        data: probabilities,
        smooth: true,
        itemStyle: {
          color: '#409EFF'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
          ])
        }
      }
    ]
  }

  chartInstance.setOption(option)
}

// 工具函数
const getRiskLevelType = (level) => {
  const types = {
    low: 'success',
    medium: 'warning',
    high: 'danger'
  }
  return types[level] || 'info'
}

const getRiskLevelText = (level) => {
  const texts = {
    low: '低风险',
    medium: '中风险',
    high: '高风险'
  }
  return texts[level] || level
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const goBack = () => {
  router.back()
}

watch(
  () => route.params.id,
  (id) => {
    if (!id) return
    loadPatient()
    loadStatistics()
    loadPredictions()
  }
)

onMounted(() => {
  loadPatient()
  loadStatistics()
  loadPredictions()
})
</script>

<style scoped>
.patient-detail {
  padding-top: 8px;
}

.info-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.phone-toggle {
  margin-left: 8px;
  vertical-align: baseline;
}

.bindings-hint {
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
  line-height: 1.5;
}

.bindings-actions {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
</style>
