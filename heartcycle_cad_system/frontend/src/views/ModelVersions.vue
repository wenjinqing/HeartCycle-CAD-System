<template>
  <div class="model-versions-container hc-page-shell">
    <el-card class="header-card hc-card-elevated" shadow="never">
      <div class="header">
        <h2>模型版本管理</h2>
        <el-button
          type="primary"
          @click="showUploadDialog = true"
          v-if="canManageModels"
        >
          <el-icon><Upload /></el-icon>
          上传新版本
        </el-button>
      </div>
    </el-card>

    <!-- 筛选条件 -->
    <el-card class="filter-card hc-card-elevated" shadow="never">
      <el-form :inline="true">
        <el-form-item label="模型名称">
          <el-input
            v-model="filters.model_name"
            placeholder="输入模型名称"
            clearable
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item label="模型类型">
          <el-select
            v-model="filters.model_type"
            placeholder="选择类型"
            clearable
            style="width: 150px"
          >
            <el-option label="逻辑回归" value="lr" />
            <el-option label="随机森林" value="rf" />
            <el-option label="XGBoost" value="xgb" />
            <el-option label="CNN" value="cnn" />
            <el-option label="LSTM" value="lstm" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filters.is_active"
            placeholder="选择状态"
            clearable
            style="width: 120px"
          >
            <el-option label="激活" :value="true" />
            <el-option label="未激活" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadVersions">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 版本列表 -->
    <el-card class="list-card hc-card-elevated" shadow="never">
      <el-table :data="versions" v-loading="loading" style="width: 100%">
        <el-table-column prop="model_name" label="模型名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.description || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本号" width="160" show-overflow-tooltip />
        <el-table-column prop="model_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.model_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="性能指标" width="300">
          <template #default="{ row }">
            <div class="metrics">
              <span v-if="row.accuracy">准确率: {{ (row.accuracy * 100).toFixed(2) }}%</span>
              <span v-if="row.auc">AUC: {{ row.auc.toFixed(4) }}</span>
              <span v-if="row.f1_score">F1: {{ row.f1_score.toFixed(4) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.is_production" type="danger">生产版本</el-tag>
            <el-tag v-else-if="row.is_active" type="success">激活</el-tag>
            <el-tag v-else type="info">未激活</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetails(row)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button
              size="small"
              type="success"
              @click="activateVersion(row)"
              v-if="!row.is_active && canManageModels"
            >
              激活
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="deleteVersion(row)"
              v-if="!row.is_active && !row.is_production && canManageModels"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadVersions"
          @current-change="loadVersions"
        />
      </div>
    </el-card>

    <!-- 上传新版本对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传新模型版本"
      width="600px"
    >
      <el-form :model="uploadForm" label-width="120px">
        <el-form-item label="模型名称" required>
          <el-input v-model="uploadForm.model_name" placeholder="如: cad_predictor" />
        </el-form-item>

        <el-form-item label="版本号" required>
          <el-input v-model="uploadForm.version" placeholder="如: 1.0.0" />
        </el-form-item>

        <el-form-item label="模型类型" required>
          <el-select v-model="uploadForm.model_type" style="width: 100%">
            <el-option label="逻辑回归 (LR)" value="lr" />
            <el-option label="随机森林 (RF)" value="rf" />
            <el-option label="XGBoost" value="xgb" />
            <el-option label="CNN" value="cnn" />
            <el-option label="LSTM" value="lstm" />
          </el-select>
        </el-form-item>

        <el-form-item label="模型文件" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            accept=".pkl,.h5,.joblib"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 .pkl, .h5, .joblib 格式
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="3"
            placeholder="版本说明"
          />
        </el-form-item>

        <el-divider>性能指标（可选）</el-divider>

        <el-form-item label="准确率">
          <el-input-number
            v-model="uploadForm.accuracy"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="4"
          />
        </el-form-item>

        <el-form-item label="精确率">
          <el-input-number
            v-model="uploadForm.precision"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="4"
          />
        </el-form-item>

        <el-form-item label="召回率">
          <el-input-number
            v-model="uploadForm.recall"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="4"
          />
        </el-form-item>

        <el-form-item label="F1分数">
          <el-input-number
            v-model="uploadForm.f1_score"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="4"
          />
        </el-form-item>

        <el-form-item label="AUC">
          <el-input-number
            v-model="uploadForm.auc"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="4"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button
          type="primary"
          @click="uploadVersion"
          :loading="uploading"
        >
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- 版本详情对话框 -->
    <el-dialog
      v-model="showDetailsDialog"
      title="模型版本详情"
      width="700px"
    >
      <el-descriptions :column="2" border v-if="selectedVersion">
        <el-descriptions-item label="模型名称">
          {{ selectedVersion.model_name }}
        </el-descriptions-item>
        <el-descriptions-item label="版本号">
          {{ selectedVersion.version }}
        </el-descriptions-item>
        <el-descriptions-item label="模型类型">
          {{ selectedVersion.model_type }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="selectedVersion.is_production" type="danger">生产版本</el-tag>
          <el-tag v-else-if="selectedVersion.is_active" type="success">激活</el-tag>
          <el-tag v-else type="info">未激活</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="准确率">
          {{ selectedVersion.accuracy ? (selectedVersion.accuracy * 100).toFixed(2) + '%' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="精确率">
          {{ selectedVersion.precision ? selectedVersion.precision.toFixed(4) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="召回率">
          {{ selectedVersion.recall ? selectedVersion.recall.toFixed(4) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="F1分数">
          {{ selectedVersion.f1_score ? selectedVersion.f1_score.toFixed(4) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="AUC">
          {{ selectedVersion.auc ? selectedVersion.auc.toFixed(4) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="训练样本数">
          {{ selectedVersion.training_samples || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="训练时长">
          {{ selectedVersion.training_time ? selectedVersion.training_time.toFixed(2) + 's' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="特征数量">
          {{ selectedVersion.feature_count || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">
          {{ formatDate(selectedVersion.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">
          {{ selectedVersion.description || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">
          {{ selectedVersion.notes || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Search, View } from '@element-plus/icons-vue'
import { api } from '../services/api'

const versions = ref([])
const loading = ref(false)
const uploading = ref(false)
const showUploadDialog = ref(false)
const showDetailsDialog = ref(false)
const selectedVersion = ref(null)
const uploadRef = ref(null)

const filters = ref({
  model_name: '',
  model_type: '',
  is_active: null
})

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const uploadForm = ref({
  model_name: '',
  version: '',
  model_type: '',
  description: '',
  file: null,
  accuracy: null,
  precision: null,
  recall: null,
  f1_score: null,
  auc: null
})

// 权限检查
const userRole = computed(() => {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  return user.role
})

const canManageModels = computed(() => {
  return ['admin', 'researcher'].includes(userRole.value)
})

// 加载版本列表
const loadVersions = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.value.page - 1) * pagination.value.pageSize,
      limit: pagination.value.pageSize
    }

    if (filters.value.model_name) {
      params.model_name = filters.value.model_name
    }
    if (filters.value.model_type) {
      params.model_type = filters.value.model_type
    }
    if (filters.value.is_active !== null) {
      params.is_active = filters.value.is_active
    }

    const response = await api.get('/model-versions', { params })
    if (response.data.success) {
      versions.value = response.data.data.versions
      pagination.value.total = response.data.data.total
    }
  } catch (error) {
    console.error('加载版本列表失败:', error)
    ElMessage.error('加载版本列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  filters.value = {
    model_name: '',
    model_type: '',
    is_active: null
  }
  pagination.value.page = 1
  loadVersions()
}

// 文件选择
const handleFileChange = (file) => {
  uploadForm.value.file = file.raw
}

// 上传版本
const uploadVersion = async () => {
  if (!uploadForm.value.model_name || !uploadForm.value.version ||
      !uploadForm.value.model_type || !uploadForm.value.file) {
    ElMessage.warning('请填写必填项并选择文件')
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadForm.value.file)
    formData.append('model_name', uploadForm.value.model_name)
    formData.append('version', uploadForm.value.version)
    formData.append('model_type', uploadForm.value.model_type)

    if (uploadForm.value.description) {
      formData.append('description', uploadForm.value.description)
    }
    if (uploadForm.value.accuracy !== null) {
      formData.append('accuracy', uploadForm.value.accuracy)
    }
    if (uploadForm.value.precision !== null) {
      formData.append('precision', uploadForm.value.precision)
    }
    if (uploadForm.value.recall !== null) {
      formData.append('recall', uploadForm.value.recall)
    }
    if (uploadForm.value.f1_score !== null) {
      formData.append('f1_score', uploadForm.value.f1_score)
    }
    if (uploadForm.value.auc !== null) {
      formData.append('auc', uploadForm.value.auc)
    }

    const response = await api.post('/model-versions', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    if (response.data.success) {
      ElMessage.success('版本上传成功')
      showUploadDialog.value = false
      resetUploadForm()
      loadVersions()
    }
  } catch (error) {
    console.error('上传版本失败:', error)
    ElMessage.error(error.response?.data?.detail || '上传版本失败')
  } finally {
    uploading.value = false
  }
}

// 重置上传表单
const resetUploadForm = () => {
  uploadForm.value = {
    model_name: '',
    version: '',
    model_type: '',
    description: '',
    file: null,
    accuracy: null,
    precision: null,
    recall: null,
    f1_score: null,
    auc: null
  }
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// 查看详情
const viewDetails = (version) => {
  selectedVersion.value = version
  showDetailsDialog.value = true
}

// 激活版本
const activateVersion = async (version) => {
  try {
    await ElMessageBox.confirm(
      `确定要激活版本 ${version.version} 吗？这将取消当前激活的版本。`,
      '确认激活',
      { type: 'warning' }
    )

    const response = await api.put(`/model-versions/${version.id}`, {
      is_active: true
    })

    if (response.data.success) {
      ElMessage.success('版本已激活')
      loadVersions()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('激活版本失败:', error)
      ElMessage.error('激活版本失败')
    }
  }
}

// 删除版本
const deleteVersion = async (version) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除版本 ${version.version} 吗？此操作不可恢复。`,
      '确认删除',
      { type: 'warning' }
    )

    const response = await api.delete(`/model-versions/${version.id}`)
    if (response.data.success) {
      ElMessage.success('版本已删除')
      loadVersions()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除版本失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除版本失败')
    }
  }
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadVersions()
})
</script>

<style scoped>
.model-versions-container {
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

.filter-card {
  margin-bottom: 20px;
}

.list-card {
  min-height: 400px;
}

.metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
