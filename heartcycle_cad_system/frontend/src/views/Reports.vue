<template>
  <div class="reports-container hc-page-shell">
    <el-card class="header-card hc-card-elevated" shadow="never">
      <div class="header">
        <h2>报告管理</h2>
        <el-button type="primary" @click="showGenerateDialog = true">
          <el-icon><Document /></el-icon>
          生成报告
        </el-button>
      </div>
    </el-card>

    <!-- 报告列表 -->
    <el-card class="list-card hc-card-elevated" shadow="never">
      <el-table :data="reports" v-loading="loading" style="width: 100%">
        <el-table-column prop="filename" label="文件名" min-width="200" />
        <el-table-column label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatFileSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="downloadReport(row.filename)"
            >
              <el-icon><Download /></el-icon>
              下载
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="deleteReport(row.filename)"
              v-if="canManageReports"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 生成报告对话框 -->
    <el-dialog
      v-model="showGenerateDialog"
      title="生成预测报告"
      width="600px"
      @opened="onGenerateDialogOpened"
      @closed="resetGenerateForm"
    >
      <el-form :model="reportForm" label-width="120px">
        <el-form-item label="患者" required>
          <el-select
            v-model="reportForm.patient_id"
            placeholder="选择患者"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="patient in patients"
              :key="patient.id"
              :label="`${patient.patient_no} - ${patient.name}`"
              :value="patient.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="预测记录" required>
          <el-select
            v-model="reportForm.prediction_id"
            placeholder="选择预测记录"
            style="width: 100%"
            :disabled="!reportForm.patient_id"
            :loading="predictionsLoading"
          >
            <el-option
              v-for="pred in predictions"
              :key="pred.id"
              :label="`${pred.created_at} - ${pred.risk_level}`"
              :value="pred.id"
            />
          </el-select>
          <div
            v-if="reportForm.patient_id && !predictionsLoading && predictions.length === 0"
            class="predictions-hint"
          >
            该患者暂无已保存的预测记录。请从
            <strong>患者列表 → 患者详情 → 新建预测</strong>
            进入监测页并完成分析（需登录），系统才会写入记录，之后即可在此生成报告。
          </div>
        </el-form-item>

        <el-form-item label="包含统计信息">
          <el-switch v-model="reportForm.include_statistics" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button
          type="primary"
          @click="generateReport"
          :loading="generating"
        >
          生成报告
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Download, Delete } from '@element-plus/icons-vue'
import { api } from '../services/api'

const reports = ref([])
const patients = ref([])
const predictions = ref([])
const predictionsLoading = ref(false)
const loading = ref(false)
const generating = ref(false)
const showGenerateDialog = ref(false)

const reportForm = ref({
  patient_id: null,
  prediction_id: null,
  include_statistics: true
})

// 权限检查
const userRole = computed(() => {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  return user.role
})

const canManageReports = computed(() => {
  return ['admin', 'doctor', 'researcher'].includes(userRole.value)
})

// 加载报告列表（axios 拦截器已返回 API 体：{ success, data }）
const loadReports = async () => {
  loading.value = true
  try {
    const res = await api.get('/reports/list')
    if (res?.success) {
      reports.value = Array.isArray(res.data) ? res.data : []
    }
  } catch (error) {
    console.error('加载报告列表失败:', error)
    ElMessage.error('加载报告列表失败')
  } finally {
    loading.value = false
  }
}

// 加载患者列表（后端 data.items，非 patients）
const loadPatients = async () => {
  try {
    const res = await api.get('/patients', {
      params: { limit: 1000 }
    })
    if (res?.success && res.data) {
      patients.value = res.data.items || []
    }
  } catch (error) {
    console.error('加载患者列表失败:', error)
    ElMessage.error('加载患者列表失败')
  }
}

const resetGenerateForm = () => {
  reportForm.value = {
    patient_id: null,
    prediction_id: null,
    include_statistics: true
  }
  predictions.value = []
  predictionsLoading.value = false
}

const loadPredictionsForPatient = async (patientId) => {
  reportForm.value.prediction_id = null
  predictions.value = []

  const id =
    patientId === null || patientId === undefined || patientId === ''
      ? NaN
      : Number(patientId)
  if (!Number.isFinite(id) || id <= 0) return

  predictionsLoading.value = true
  try {
    const res = await api.get(`/patients/${id}/predictions`, {
      params: { limit: 500, skip: 0 }
    })
    if (res?.success && res.data != null) {
      const raw = res.data
      const items = Array.isArray(raw.items)
        ? raw.items
        : Array.isArray(raw)
          ? raw
          : []
      predictions.value = items
    }
  } catch (error) {
    console.error('加载预测记录失败:', error)
    ElMessage.error('加载预测记录失败')
  } finally {
    predictionsLoading.value = false
  }
}

watch(
  () => reportForm.value.patient_id,
  (pid) => {
    loadPredictionsForPatient(pid)
  }
)

const onGenerateDialogOpened = () => {
  if (reportForm.value.patient_id != null) {
    loadPredictionsForPatient(reportForm.value.patient_id)
  }
}

// 生成报告
const generateReport = async () => {
  if (!reportForm.value.patient_id || !reportForm.value.prediction_id) {
    ElMessage.warning('请选择患者和预测记录')
    return
  }

  generating.value = true
  try {
    const res = await api.post('/reports/prediction', reportForm.value)
    if (res?.success && res.data?.filename) {
      ElMessage.success('报告生成成功')
      showGenerateDialog.value = false
      loadReports()

      // 自动下载
      downloadReport(res.data.filename)
    }
  } catch (error) {
    console.error('生成报告失败:', error)
    ElMessage.error(error.response?.data?.detail || '生成报告失败')
  } finally {
    generating.value = false
  }
}

// 下载报告（blob 请求拦截器直接返回 Blob）
const downloadReport = async (filename) => {
  try {
    const blob = await api.get(
      `/reports/download/${encodeURIComponent(filename)}`,
      { responseType: 'blob' }
    )

    const url = window.URL.createObjectURL(
      blob instanceof Blob ? blob : new Blob([blob])
    )
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('下载成功')
  } catch (error) {
    console.error('下载报告失败:', error)
    ElMessage.error('下载报告失败')
  }
}

// 删除报告
const deleteReport = async (filename) => {
  try {
    await ElMessageBox.confirm('确定要删除这个报告吗？', '确认删除', {
      type: 'warning'
    })

    const res = await api.delete(`/reports/${encodeURIComponent(filename)}`)
    if (res?.success) {
      ElMessage.success('删除成功')
      loadReports()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除报告失败:', error)
      ElMessage.error('删除报告失败')
    }
  }
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadReports()
  loadPatients()
})
</script>

<style scoped>
.reports-container {
  padding-top: 4px;
}

.header-card {
  margin-bottom: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.list-card {
  min-height: 400px;
}

.predictions-hint {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #909399;
}
</style>
