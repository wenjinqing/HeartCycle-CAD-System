<template>
  <div class="train-h5-auto">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon><DataAnalysis /></el-icon>
          <span>H5文件快速训练（自动识别标签）</span>
        </div>
      </template>

      <!-- 说明区域 -->
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #title>
          <strong>✨ 智能标签识别</strong>
        </template>
        <div style="line-height: 1.8">
          只需上传H5文件，系统会自动：<br/>
          1. 📁 在H5文件目录中查找 <code>SubjectMetadata.csv</code> 文件<br/>
          2. 🏷️ 从元数据中提取 <code>Disease_Status</code> 字段作为标签<br/>
          3. 🔄 将 "Healthy" 转换为 0，其他疾病状态转换为 1<br/>
          4. 🚀 自动启动模型训练<br/>
        </div>
      </el-alert>

      <el-steps :active="currentStep" finish-status="success" align-center style="margin-bottom: 30px">
        <el-step title="上传H5文件" description="选择训练数据" />
        <el-step title="配置参数" description="设置训练选项" />
        <el-step title="开始训练" description="启动训练任务" />
      </el-steps>

      <!-- 步骤1: 上传H5文件 -->
      <div v-if="currentStep === 0" class="step-panel">
        <el-form label-width="140px">
          <el-form-item label="H5数据文件" required>
            <el-upload
              ref="h5UploadRef"
              :auto-upload="false"
              :on-change="handleH5FilesChange"
              :on-remove="handleH5FilesRemove"
              :file-list="fileList"
              multiple
              accept=".h5"
              drag
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                拖拽H5文件到此处或 <em>点击选择</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持选择多个H5文件，系统会自动识别标签并进行训练
                </div>
              </template>
            </el-upload>
          </el-form-item>

          <!-- 文件列表 -->
          <el-form-item v-if="selectedH5Files.length > 0" label="已选择的文件">
            <div class="file-list">
              <el-scrollbar max-height="300px">
                <div class="file-item" v-for="(file, index) in selectedH5Files" :key="index">
                  <el-icon><Document /></el-icon>
                  <span class="file-name">{{ file.name }}</span>
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  <el-button
                    link
                    type="danger"
                    @click="removeH5File(index)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </el-scrollbar>
              <el-divider />
              <el-text type="success" size="large">
                <el-icon><SuccessFilled /></el-icon>
                共选择 {{ selectedH5Files.length }} 个H5文件
              </el-text>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              size="large"
              @click="nextStep"
              :disabled="selectedH5Files.length === 0"
            >
              下一步：配置参数
              <el-icon class="el-icon--right"><Right /></el-icon>
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤2: 配置参数 -->
      <div v-if="currentStep === 1" class="step-panel">
        <el-form :model="trainConfig" label-width="160px">
          <el-form-item label="模型类型">
            <el-select v-model="trainConfig.model_type" style="width: 200px">
              <el-option label="逻辑回归 (LR)" value="lr" />
              <el-option label="支持向量机 (SVM)" value="svm" />
              <el-option label="随机森林 (RF)" value="rf" />
              <el-option label="XGBoost" value="xgb" />
              <el-option label="LightGBM" value="lgb" />
              <el-option label="集成模型 (Stacking)" value="stacking" />
              <el-option label="投票模型 (Voting)" value="voting" />
            </el-select>
          </el-form-item>

          <el-form-item label="交叉验证折数">
            <el-input-number
              v-model="trainConfig.cv_folds"
              :min="2"
              :max="10"
              :step="1"
            />
            <span style="margin-left: 10px; color: #909399; font-size: 12px">
              用于评估模型性能
            </span>
          </el-form-item>

          <el-form-item label="高级选项">
            <el-checkbox v-model="trainConfig.use_smote">
              使用SMOTE处理数据不平衡
            </el-checkbox>
            <br/>
            <el-checkbox v-model="trainConfig.optimize_hyperparams">
              自动超参数优化（耗时较长）
            </el-checkbox>
          </el-form-item>

          <el-form-item label="特征提取选项">
            <el-checkbox v-model="trainConfig.use_existing_rpeaks">
              使用已有R波标注
            </el-checkbox>
            <br/>
            <el-checkbox v-model="trainConfig.extract_hrv">
              提取HRV特征
            </el-checkbox>
            <br/>
            <el-checkbox v-model="trainConfig.extract_clinical">
              提取临床特征
            </el-checkbox>
          </el-form-item>

          <el-form-item label="随机种子">
            <el-input-number
              v-model="trainConfig.random_state"
              :min="0"
              :max="9999"
            />
            <span style="margin-left: 10px; color: #909399; font-size: 12px">
              保证结果可复现
            </span>
          </el-form-item>

          <el-form-item>
            <el-button @click="prevStep">
              <el-icon><Back /></el-icon>
              上一步
            </el-button>
            <el-button type="primary" size="large" @click="nextStep" style="margin-left: 10px">
              下一步：确认训练
              <el-icon class="el-icon--right"><Right /></el-icon>
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 步骤3: 确认并开始训练 -->
      <div v-if="currentStep === 2" class="step-panel">
        <el-descriptions
          title="训练配置确认"
          :column="2"
          border
          style="margin-bottom: 20px"
        >
          <el-descriptions-item label="H5文件数量">
            {{ selectedH5Files.length }} 个
          </el-descriptions-item>
          <el-descriptions-item label="模型类型">
            {{ getModelTypeName(trainConfig.model_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="交叉验证">
            {{ trainConfig.cv_folds }} 折
          </el-descriptions-item>
          <el-descriptions-item label="SMOTE">
            {{ trainConfig.use_smote ? '启用' : '禁用' }}
          </el-descriptions-item>
          <el-descriptions-item label="超参数优化">
            {{ trainConfig.optimize_hyperparams ? '启用' : '禁用' }}
          </el-descriptions-item>
          <el-descriptions-item label="标签识别">
            自动识别（SubjectMetadata.csv）
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="!isTraining && !trainResult"
          type="warning"
          :closable="false"
          style="margin-bottom: 20px"
        >
          <strong>注意：</strong>训练可能需要几分钟到几十分钟，请耐心等待
        </el-alert>

        <!-- 训练进度 -->
        <div v-if="isTraining" class="training-progress">
          <el-card shadow="never">
            <div style="text-align: center">
              <el-icon class="is-loading" :size="60" color="#409EFF">
                <Loading />
              </el-icon>
              <h3 style="margin-top: 20px">{{ trainingStatus }}</h3>
              <el-progress
                :percentage="trainingProgress"
                :indeterminate="trainingProgress === 0"
                style="margin-top: 20px"
              />
              <p style="margin-top: 10px; color: #909399">
                任务ID: {{ taskId }}
              </p>
            </div>
          </el-card>
        </div>

        <!-- 训练结果 -->
        <div v-if="trainResult" class="training-result">
          <el-result
            :icon="trainResult.success ? 'success' : 'error'"
            :title="trainResult.success ? '训练完成！' : '训练失败'"
            :sub-title="trainResult.message"
          >
            <template #extra>
              <el-button type="primary" @click="viewResults" v-if="trainResult.success">
                查看详细结果
              </el-button>
              <el-button @click="resetTraining">重新训练</el-button>
            </template>
          </el-result>

          <!-- 标签统计 -->
          <el-card v-if="labelStats" shadow="never" style="margin-top: 20px">
            <template #header>
              标签识别统计
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="总文件数">
                {{ labelStats.total_files }}
              </el-descriptions-item>
              <el-descriptions-item label="健康样本">
                {{ labelStats.label_0_count }} ({{ ((labelStats.label_0_count / labelStats.total_files) * 100).toFixed(1) }}%)
              </el-descriptions-item>
              <el-descriptions-item label="疾病样本">
                {{ labelStats.label_1_count }} ({{ ((labelStats.label_1_count / labelStats.total_files) * 100).toFixed(1) }}%)
              </el-descriptions-item>
              <el-descriptions-item label="元数据文件">
                {{ labelStats.metadata_found ? '✅ 已找到' : '❌ 未找到' }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </div>

        <!-- 操作按钮 -->
        <el-form-item v-if="!isTraining && !trainResult">
          <el-button @click="prevStep">
            <el-icon><Back /></el-icon>
            上一步
          </el-button>
          <el-button
            type="primary"
            size="large"
            @click="startTraining"
            :loading="isUploading"
            style="margin-left: 10px"
          >
            <el-icon v-if="!isUploading"><VideoPlay /></el-icon>
            {{ isUploading ? '上传中...' : '开始训练' }}
          </el-button>
        </el-form-item>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataAnalysis,
  UploadFilled,
  Document,
  Delete,
  Right,
  Back,
  Loading,
  VideoPlay,
  SuccessFilled
} from '@element-plus/icons-vue'
import api from '@/services/api'

// 步骤
const currentStep = ref(0)

// H5文件
const h5UploadRef = ref(null)
const selectedH5Files = ref([])
const fileList = ref([])

// 训练配置
const trainConfig = reactive({
  model_type: 'rf',  // 默认使用随机森林（对不平衡数据更稳健）
  cv_folds: 5,
  random_state: 42,
  use_smote: true,  // 启用SMOTE处理不平衡
  optimize_hyperparams: false,  // 首次训练关闭以节省时间
  use_existing_rpeaks: true,
  extract_hrv: true,
  extract_clinical: true
})

// 训练状态
const isUploading = ref(false)
const isTraining = ref(false)
const taskId = ref('')
const trainingStatus = ref('准备中...')
const trainingProgress = ref(0)
const trainResult = ref(null)
const labelStats = ref(null)

// 文件处理
const handleH5FilesChange = (file, files) => {
  selectedH5Files.value = files.map(f => f.raw)
  fileList.value = files
}

const handleH5FilesRemove = (file, files) => {
  selectedH5Files.value = files.map(f => f.raw)
  fileList.value = files
}

const removeH5File = (index) => {
  selectedH5Files.value.splice(index, 1)
  fileList.value.splice(index, 1)
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// 获取模型类型名称
const getModelTypeName = (type) => {
  const names = {
    'lr': '逻辑回归',
    'svm': '支持向量机',
    'rf': '随机森林',
    'xgb': 'XGBoost',
    'lgb': 'LightGBM',
    'stacking': '集成模型',
    'voting': '投票模型'
  }
  return names[type] || type
}

// 步骤导航
const nextStep = () => {
  if (currentStep.value < 2) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

// 上传H5文件到服务器
const uploadH5Files = async () => {
  const uploadedPaths = []

  for (const file of selectedH5Files.value) {
    try {
      // 直接传入file对象，uploadFile方法会自动创建FormData
      // 注意：axios响应拦截器已经返回了response.data，所以response就是数据对象
      const data = await api.uploadFile(file)
      if (data && data.success) {
        uploadedPaths.push(data.file_path)
      } else {
        throw new Error('上传响应格式错误')
      }
    } catch (error) {
      throw new Error(`文件 ${file.name} 上传失败: ${error.message}`)
    }
  }

  return uploadedPaths
}

// 开始训练
const startTraining = async () => {
  try {
    isUploading.value = true
    trainingStatus.value = '上传文件中...'

    // 1. 上传H5文件
    const h5FilePaths = await uploadH5Files()

    isUploading.value = false
    isTraining.value = true
    trainingStatus.value = '正在识别标签...'
    trainingProgress.value = 10

    // 2. 调用自动标签识别训练API
    const data = await api.trainFromH5Auto({
      h5_files: h5FilePaths,
      auto_detect_labels: true,
      ...trainConfig
    })

    // 响应拦截器已返回data，不需要再访问response.data
    if (data && data.success) {
      taskId.value = data.data.task_id
      labelStats.value = data.data.label_stats

      ElMessage.success('训练任务已启动，正在识别标签...')

      // 3. 轮询训练状态
      pollTrainingStatus()
    } else {
      throw new Error(data?.message || '启动训练失败')
    }
  } catch (error) {
    isUploading.value = false
    isTraining.value = false
    ElMessage.error(error.message || '启动训练失败')
    trainResult.value = {
      success: false,
      message: error.message || '启动训练失败'
    }
  }
}

// 轮询训练状态
const pollTrainingStatus = async () => {
  const pollInterval = setInterval(async () => {
    try {
      const data = await api.getH5TrainingStatus(taskId.value)
      // 响应拦截器已返回data，data就是{success: true, data: {...}}
      const statusData = data.data

      if (statusData.status === 'running') {
        trainingStatus.value = statusData.message || '训练中...'
        trainingProgress.value = statusData.progress || 50
      } else if (statusData.status === 'completed') {
        clearInterval(pollInterval)
        isTraining.value = false
        trainingProgress.value = 100
        trainResult.value = {
          success: true,
          message: '模型训练成功！',
          data: statusData.result
        }
        ElMessage.success('训练完成！')
      } else if (statusData.status === 'failed') {
        clearInterval(pollInterval)
        isTraining.value = false
        trainResult.value = {
          success: false,
          message: statusData.error || '训练失败'
        }
        ElMessage.error('训练失败')
      }
    } catch (error) {
      console.error('查询训练状态失败:', error)
    }
  }, 3000) // 每3秒查询一次
}

// 查看结果
const viewResults = () => {
  ElMessageBox.alert(
    JSON.stringify(trainResult.value.data, null, 2),
    '训练结果',
    {
      confirmButtonText: '确定',
      customClass: 'result-message-box'
    }
  )
}

// 重置训练
const resetTraining = () => {
  currentStep.value = 0
  selectedH5Files.value = []
  fileList.value = []
  isTraining.value = false
  isUploading.value = false
  taskId.value = ''
  trainingProgress.value = 0
  trainResult.value = null
  labelStats.value = null
}
</script>

<style scoped>
.train-h5-auto {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
}

.step-panel {
  margin-top: 30px;
  padding: 20px;
}

.file-list {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 15px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.file-item:last-child {
  border-bottom: none;
}

.file-name {
  flex: 1;
  margin-left: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.training-progress {
  margin: 30px 0;
}

.training-result {
  margin-top: 20px;
}

code {
  padding: 2px 6px;
  background-color: #f5f7fa;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  color: #409EFF;
}

:deep(.el-upload-dragger) {
  padding: 40px 20px;
}

:deep(.result-message-box) {
  width: 600px;
}

:deep(.result-message-box .el-message-box__message) {
  max-height: 400px;
  overflow: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre;
}
</style>
