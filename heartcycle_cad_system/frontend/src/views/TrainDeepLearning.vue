<template>
  <div class="deep-learning-container hc-page-shell">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>深度学习模型训练</span>
          <el-button type="primary" @click="showModelTypesDialog">模型类型说明</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
        title="HeartCycle 等结构的 H5（ECG 在 measure/_030）已支持；若文件内无根级 label/cad，将自动使用演示标签训练。"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="140px"
        label-position="left"
      >
        <el-form-item label="H5文件" prop="h5_files">
          <el-select
            v-model="form.h5_files"
            multiple
            filterable
            placeholder="请选择H5文件"
            style="width: 100%"
            @change="onH5FilesChange"
          >
            <el-option
              v-for="file in h5Files"
              :key="file"
              :label="basename(file)"
              :value="file"
              :title="file"
            />
          </el-select>
          <div class="form-tip">
            已选择 {{ form.h5_files.length }} 个文件（至少 10 个以满足划分与验证）
          </div>
        </el-form-item>

        <el-form-item label="模型类型" prop="model_type">
          <el-select v-model="form.model_type" placeholder="请选择模型类型">
            <el-option label="1D-CNN（推荐）" value="cnn" />
            <el-option label="LSTM" value="lstm" />
            <el-option label="GRU" value="gru" />
            <el-option label="CNN-LSTM（最佳性能）" value="cnn_lstm" />
          </el-select>
        </el-form-item>

        <el-form-item label="信号长度" prop="signal_length">
          <el-input-number
            v-model="form.signal_length"
            :min="1000"
            :max="10000"
            :step="1000"
          />
          <span class="form-tip">采样点数，默认5000</span>
        </el-form-item>

        <el-form-item label="训练轮数" prop="epochs">
          <el-input-number
            v-model="form.epochs"
            :min="10"
            :max="200"
            :step="10"
          />
          <span class="form-tip">Epochs，建议50-100</span>
        </el-form-item>

        <el-form-item label="批次大小" prop="batch_size">
          <el-input-number
            v-model="form.batch_size"
            :min="8"
            :max="256"
            :step="8"
          />
          <span class="form-tip">Batch Size，建议32</span>
        </el-form-item>

        <el-form-item label="学习率" prop="learning_rate">
          <el-input-number
            v-model="form.learning_rate"
            :min="0.0001"
            :max="0.01"
            :step="0.0001"
            :precision="4"
          />
          <span class="form-tip">Learning Rate，建议0.001</span>
        </el-form-item>

        <el-form-item label="测试集比例" prop="test_size">
          <el-slider
            v-model="form.test_size"
            :min="0.1"
            :max="0.4"
            :step="0.05"
            :format-tooltip="(val) => `${(val * 100).toFixed(0)}%`"
          />
        </el-form-item>

        <el-form-item label="验证集比例" prop="validation_split">
          <el-slider
            v-model="form.validation_split"
            :min="0.1"
            :max="0.3"
            :step="0.05"
            :format-tooltip="(val) => `${(val * 100).toFixed(0)}%`"
          />
        </el-form-item>

        <el-form-item label="模型校准">
          <el-switch v-model="form.use_calibration" />
          <span class="form-tip">提高概率预测的可靠性</span>
        </el-form-item>

        <el-form-item label="校准方法" prop="calibration_method" v-if="form.use_calibration">
          <el-radio-group v-model="form.calibration_method">
            <el-radio value="platt">Platt Scaling（推荐）</el-radio>
            <el-radio value="isotonic">Isotonic Regression</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleTrain" :loading="training">
            开始训练
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <h3>已训练的深度学习模型</h3>
      <el-table :data="models" v-loading="loadingModels" stripe>
        <el-table-column prop="model_id" label="模型ID" width="200" />
        <el-table-column prop="model_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ getModelTypeName(row.model_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="test_accuracy" label="准确率" width="100">
          <template #default="{ row }">
            {{ (row.test_accuracy * 100).toFixed(2) }}%
          </template>
        </el-table-column>
        <el-table-column prop="test_auc" label="AUC" width="100">
          <template #default="{ row }">
            {{ row.test_auc.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="use_calibration" label="校准" width="80">
          <template #default="{ row }">
            <el-tag :type="row.use_calibration ? 'success' : 'info'">
              {{ row.use_calibration ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewModelDetail(row)">
              查看详情
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 模型类型说明对话框 -->
    <el-dialog v-model="modelTypesDialogVisible" title="深度学习模型类型说明" width="800px">
      <el-descriptions :column="1" border v-for="(info, type) in modelTypes" :key="type">
        <el-descriptions-item label="模型名称">
          <el-tag size="large">{{ info.name }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="描述">
          {{ info.description }}
        </el-descriptions-item>
        <el-descriptions-item label="优势">
          <el-tag v-for="adv in info.advantages" :key="adv" style="margin-right: 5px">
            {{ adv }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="推荐场景">
          {{ info.recommended_for }}
        </el-descriptions-item>
      </el-descriptions>
      <el-divider v-if="Object.keys(modelTypes).length > 1" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiService } from '@/services/api'

const router = useRouter()

const formRef = ref(null)
const training = ref(false)
const loadingModels = ref(false)
const h5Files = ref([])
const models = ref([])
const modelTypesDialogVisible = ref(false)
const modelTypes = ref({})

const form = reactive({
  h5_files: [],
  model_type: 'cnn',
  signal_length: 5000,
  epochs: 50,
  batch_size: 32,
  learning_rate: 0.001,
  test_size: 0.2,
  validation_split: 0.2,
  use_calibration: true,
  calibration_method: 'platt'
})

const rules = {
  h5_files: [
    { required: true, message: '请选择H5文件', trigger: 'change' },
    { type: 'array', min: 10, message: '至少选择10个文件', trigger: 'change' }
  ],
  model_type: [
    { required: true, message: '请选择模型类型', trigger: 'change' }
  ]
}

function normPath(p) {
  if (p == null || typeof p !== 'string') return p
  return p.trim().replace(/\\/g, '/')
}

function basename(p) {
  const n = normPath(p)
  if (!n) return ''
  const i = Math.max(n.lastIndexOf('/'), n.lastIndexOf('\\'))
  return i >= 0 ? n.slice(i + 1) : n
}

/** 与下拉选项中的路径字符串完全一致，避免 el-select 报 value 无效 */
function canonicalH5Path(p) {
  const n = normPath(p)
  const hit = h5Files.value.find((h) => normPath(h) === n)
  return hit != null ? hit : p
}

function onH5FilesChange() {
  form.h5_files = (form.h5_files || []).map(canonicalH5Path)
}

const getModelTypeName = (type) => {
  const names = {
    cnn: '1D-CNN',
    lstm: 'LSTM',
    gru: 'GRU',
    cnn_lstm: 'CNN-LSTM'
  }
  return names[type] || type
}

const loadH5Files = async () => {
  try {
    const response = await apiService.getFiles()
    if (response.success) {
      const files = response.files || []
      const paths = files
        .filter((f) => f.filename && f.filename.endsWith('.h5'))
        .map((f) => normPath(f.path))
      h5Files.value = paths
      // 刷新列表后去掉已不存在的选中项，并把保留项规范成与 options 完全相同的字符串
      form.h5_files = (form.h5_files || [])
        .map((p) => canonicalH5Path(p))
        .filter((p) => paths.some((x) => normPath(x) === normPath(p)))
    } else {
      ElMessage.error(response.message || '获取H5文件列表失败')
    }
  } catch (error) {
    const d = error.response?.data?.detail
    ElMessage.error(
      typeof d === 'string' ? d : error.message || '获取H5文件列表失败'
    )
  }
}

const loadModels = async () => {
  loadingModels.value = true
  try {
    const response = await apiService.getDeepLearningModels()
    if (response.success) {
      models.value = response.data
    }
  } catch (error) {
    ElMessage.error('获取模型列表失败')
  } finally {
    loadingModels.value = false
  }
}

const loadModelTypes = async () => {
  try {
    const response = await apiService.getDeepLearningModelTypes()
    if (response.success) {
      modelTypes.value = response.data
    }
  } catch (error) {
    console.error('获取模型类型失败:', error)
  }
}

const showModelTypesDialog = async () => {
  modelTypesDialogVisible.value = true
  await loadModelTypes()
}

const handleTrain = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    training.value = true
    try {
      const h5_files = (form.h5_files || []).map(canonicalH5Path)
      const payload = {
        h5_files,
        model_type: form.model_type,
        signal_length: form.signal_length,
        epochs: form.epochs,
        batch_size: form.batch_size,
        learning_rate: form.learning_rate,
        test_size: form.test_size,
        validation_split: form.validation_split,
        use_calibration: form.use_calibration,
        calibration_method: form.calibration_method
      }
      const response = await apiService.trainDeepLearningModel(payload)

      if (response.success) {
        ElMessage.success('深度学习模型训练成功')
        loadModels()
      } else {
        ElMessage.error(response.message || '训练失败')
      }
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '训练失败')
    } finally {
      training.value = false
    }
  })
}

const handleDelete = async (model) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型 "${model.model_id}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await apiService.deleteDeepLearningModel(model.model_id)
    if (response.success) {
      ElMessage.success('模型已删除')
      loadModels()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const viewModelDetail = (model) => {
  router.push(`/models/${model.model_id}`)
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

onMounted(() => {
  loadH5Files()
  loadModels()
  loadModelTypes()
})
</script>

<style scoped>
.deep-learning-container {
  padding-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

h3 {
  margin-bottom: 20px;
  color: #303133;
}
</style>
