<template>
  <div class="train-model">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon><Setting /></el-icon>
          <span>模型训练</span>
        </div>
      </template>

      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="上传数据" description="上传特征和标签文件" />
        <el-step title="配置参数" description="设置模型训练参数" />
        <el-step title="训练模型" description="执行模型训练" />
        <el-step title="查看结果" description="查看训练结果" />
      </el-steps>

      <div class="step-content">
        <!-- 步骤1: 上传数据 -->
        <div v-if="currentStep === 0" class="step-panel">
          <el-form label-width="150px">
            <el-form-item label="特征文件 (CSV)">
              <el-upload
                ref="featureUploadRef"
                :auto-upload="false"
                :on-change="handleFeatureFileChange"
                :on-remove="handleFeatureFileRemove"
                :limit="1"
                accept=".csv"
              >
                <el-button type="primary">
                  <el-icon><Upload /></el-icon>
                  选择特征文件
                </el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    CSV格式，包含特征列（如：age, gender, height, weight, bmi, mean_rr, sdnn, rmssd, pnn50, lf_hf_ratio）
                  </div>
                </template>
              </el-upload>
              <div v-if="featureFile" class="file-info">
                <el-tag type="info" style="margin-top: 10px">
                  <el-icon><Document /></el-icon>
                  {{ featureFile.name }} ({{ formatFileSize(featureFile.size) }})
                </el-tag>
              </div>
            </el-form-item>

            <el-form-item label="标签文件 (CSV)">
              <el-upload
                ref="labelUploadRef"
                :auto-upload="false"
                :on-change="handleLabelFileChange"
                :on-remove="handleLabelFileRemove"
                :limit="1"
                accept=".csv"
              >
                <el-button type="primary">
                  <el-icon><Upload /></el-icon>
                  选择标签文件
                </el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    CSV格式，包含一列标签（0=健康，1=CAD）
                  </div>
                </template>
              </el-upload>
              <div v-if="labelFile" class="file-info">
                <el-tag type="info" style="margin-top: 10px">
                  <el-icon><Document /></el-icon>
                  {{ labelFile.name }} ({{ formatFileSize(labelFile.size) }})
                </el-tag>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" size="large" @click="uploadFiles" :loading="uploading" :disabled="!featureFile || !labelFile">
                <el-icon v-if="!uploading"><Upload /></el-icon>
                {{ uploading ? '上传中...' : '上传并继续' }}
              </el-button>
              <el-button size="large" @click="currentStep = 0" style="margin-left: 10px">
                <el-icon><RefreshLeft /></el-icon>
                重新选择
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤2: 配置参数 -->
        <div v-if="currentStep === 1" class="step-panel">
          <el-form :model="trainConfig" label-width="150px">
            <el-form-item label="模型类型">
                <el-radio-group v-model="trainConfig.model_type">
                <el-radio value="lr">逻辑回归 (LR)</el-radio>
                <el-radio value="svm">支持向量机 (SVM)</el-radio>
                <el-radio value="rf">随机森林 (RF)</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="交叉验证折数">
              <el-input-number
                v-model="trainConfig.cv_folds"
                :min="2"
                :max="10"
                style="width: 200px"
              />
              <span style="margin-left: 10px; color: #909399">推荐: 5</span>
            </el-form-item>

            <el-form-item label="随机种子">
              <el-input-number
                v-model="trainConfig.random_state"
                :min="0"
                style="width: 200px"
              />
            </el-form-item>

            <el-form-item label="模型描述">
              <el-input
                v-model="trainConfig.description"
                type="textarea"
                :rows="3"
                placeholder="可选：为模型添加描述信息"
                style="width: 400px"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" size="large" @click="currentStep = 2" :disabled="!uploadedFeatureFile || !uploadedLabelFile">
                <el-icon><Right /></el-icon>
                下一步：配置参数
              </el-button>
              <el-button size="large" @click="currentStep = 0" style="margin-left: 20px">
                <el-icon><ArrowLeft /></el-icon>
                返回上一步
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤3: 训练模型 -->
        <div v-if="currentStep === 2" class="step-panel">
          <!-- 准备训练状态 -->
          <div v-if="!trainingStarted && !training && !trainingResult">
            <el-card>
              <template #header>
                <span>训练配置确认</span>
              </template>
              <el-descriptions :column="2" border style="margin-bottom: 20px">
                <el-descriptions-item label="特征文件">
                  {{ uploadedFeatureFile || '未上传' }}
                </el-descriptions-item>
                <el-descriptions-item label="标签文件">
                  {{ uploadedLabelFile || '未上传' }}
                </el-descriptions-item>
                <el-descriptions-item label="模型类型">
                  {{ getModelTypeName(trainConfig.model_type) }}
                </el-descriptions-item>
                <el-descriptions-item label="交叉验证">
                  {{ trainConfig.cv_folds }}折
                </el-descriptions-item>
                <el-descriptions-item label="随机种子">
                  {{ trainConfig.random_state }}
                </el-descriptions-item>
              </el-descriptions>
              <div style="text-align: center; margin-top: 30px">
                <el-button type="primary" size="large" @click="startTraining" :disabled="!uploadedFeatureFile || !uploadedLabelFile" :loading="training">
                  <el-icon v-if="!training"><VideoPlay /></el-icon>
                  {{ training ? '训练中...' : '开始训练模型' }}
                </el-button>
                <el-button size="large" @click="currentStep = 1" style="margin-left: 20px">
                  <el-icon><ArrowLeft /></el-icon>
                  返回上一步
                </el-button>
              </div>
            </el-card>
          </div>

          <!-- 训练中状态 -->
          <div v-else-if="training" class="training-status">
            <el-result v-if="training" icon="info">
              <template #icon>
                <el-icon class="is-loading" :size="60"><Loading /></el-icon>
              </template>
              <template #title>正在训练模型...</template>
              <template #sub-title>请稍候，训练可能需要几分钟时间</template>
            </el-result>

            <div v-else-if="trainingResult" class="training-result">
              <el-alert
                :title="trainingResult.success ? '训练成功' : '训练失败'"
                :type="trainingResult.success ? 'success' : 'error'"
                :closable="false"
                show-icon
              >
                <template #default v-if="trainingResult.success">
                  <p><strong>模型ID:</strong> {{ trainingResult.model_id }}</p>
                  <p v-if="trainingResult.metrics">
                    <strong>AUC:</strong> {{ trainingResult.metrics.roc_auc?.mean?.toFixed(4) || 'N/A' }}
                  </p>
                  <p v-if="trainingResult.metrics">
                    <strong>准确率:</strong> {{ trainingResult.metrics.accuracy?.mean?.toFixed(4) || 'N/A' }}
                  </p>
                </template>
              </el-alert>
              <div style="margin-top: 20px">
                <el-button type="primary" size="large" @click="viewResults">
                  <el-icon><ViewIcon /></el-icon>
                  查看详细结果
                </el-button>
                <el-button size="large" @click="resetTraining" style="margin-left: 10px">
                  <el-icon><RefreshLeft /></el-icon>
                  重新训练
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤4: 查看结果 -->
        <div v-if="currentStep === 3" class="step-panel">
          <el-card v-if="trainingResult && trainingResult.success">
            <template #header>
              <span>训练结果详情</span>
            </template>

            <el-descriptions :column="2" border>
              <el-descriptions-item label="模型ID">
                <el-tag>{{ trainingResult.model_id }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="模型类型">
                {{ getModelTypeName(trainingResult.model_type) }}
              </el-descriptions-item>
              <el-descriptions-item label="样本数">
                {{ trainingResult.n_samples }}
              </el-descriptions-item>
              <el-descriptions-item label="特征数">
                {{ trainingResult.n_features }}
              </el-descriptions-item>
            </el-descriptions>

            <el-divider>性能指标</el-divider>

            <el-table :data="metricsTable" style="margin-top: 20px">
              <el-table-column prop="metric" label="指标" width="150" />
              <el-table-column prop="mean" label="均值" width="150" />
              <el-table-column prop="std" label="标准差" width="150" />
            </el-table>

            <div style="margin-top: 30px">
              <el-button type="primary" size="large" @click="goToMonitor">
                <el-icon><Right /></el-icon>
                使用模型进行预测
              </el-button>
              <el-button size="large" @click="resetTraining" style="margin-left: 10px">
                <el-icon><Plus /></el-icon>
                训练新模型
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, Upload, Document, VideoPlay, Loading, RefreshLeft, Right, ArrowLeft, View as ViewIcon, Plus } from '@element-plus/icons-vue'
import { apiService } from '../services/api'

export default {
  name: 'TrainModel',
  components: {
    Setting,
    Upload,
    Document,
    VideoPlay,
    Loading,
    RefreshLeft,
    Right,
    ArrowLeft,
    ViewIcon,
    Plus
  },
  setup() {
    const router = useRouter()
    const currentStep = ref(0)
    const featureUploadRef = ref(null)
    const labelUploadRef = ref(null)
    const featureFile = ref(null)
    const labelFile = ref(null)
    const uploading = ref(false)
    const uploadedFeatureFile = ref('')
    const uploadedLabelFile = ref('')
    const training = ref(false)
    const trainingStarted = ref(false)
    const trainingResult = ref(null)

    const trainConfig = ref({
      model_type: 'rf',
      cv_folds: 5,
      random_state: 42,
      description: ''
    })

    const handleFeatureFileChange = (file) => {
      if (file.raw) {
        featureFile.value = file.raw
      }
    }

    const handleFeatureFileRemove = () => {
      featureFile.value = null
      uploadedFeatureFile.value = ''
    }

    const handleLabelFileChange = (file) => {
      if (file.raw) {
        labelFile.value = file.raw
      }
    }

    const handleLabelFileRemove = () => {
      labelFile.value = null
      uploadedLabelFile.value = ''
    }

    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    const uploadFiles = async () => {
      if (!featureFile.value || !labelFile.value) {
        ElMessage.warning('请选择特征文件和标签文件')
        return
      }

      try {
        uploading.value = true

        // 上传特征文件
        ElMessage.info('正在上传特征文件...')
        const featureResponse = await apiService.uploadFile(featureFile.value)
        // 处理不同的响应格式
        let featureResult = featureResponse
        if (featureResponse.data) {
          featureResult = featureResponse.data
        } else if (featureResponse.file_path) {
          featureResult = featureResponse
        }
        uploadedFeatureFile.value = featureResult.file_path

        // 上传标签文件
        ElMessage.info('正在上传标签文件...')
        const labelResponse = await apiService.uploadFile(labelFile.value)
        // 处理不同的响应格式
        let labelResult = labelResponse
        if (labelResponse.data) {
          labelResult = labelResponse.data
        } else if (labelResponse.file_path) {
          labelResult = labelResponse
        }
        uploadedLabelFile.value = labelResult.file_path

        uploading.value = false
        ElMessage.success('文件上传成功，请配置训练参数')
        currentStep.value = 1
      } catch (error) {
        uploading.value = false
        ElMessage.error(`文件上传失败: ${error.message}`)
        console.error('上传错误:', error)
      }
    }

    const getModelTypeName = (type) => {
      const names = {
        'lr': '逻辑回归',
        'svm': '支持向量机',
        'rf': '随机森林'
      }
      return names[type] || type
    }

    const startTraining = async () => {
      try {
        training.value = true
        trainingStarted.value = true

        ElMessage.info('开始训练模型，请稍候...')

        const response = await apiService.trainModel({
          feature_file: uploadedFeatureFile.value,
          label_file: uploadedLabelFile.value,
          model_type: trainConfig.value.model_type,
          cv_folds: trainConfig.value.cv_folds,
          random_state: trainConfig.value.random_state
        })

        const result = response.data || response
        trainingResult.value = {
          success: true,
          ...result
        }

        training.value = false
        ElMessage.success('模型训练成功！')
        currentStep.value = 3
      } catch (error) {
        training.value = false
        trainingStarted.value = false
        ElMessage.error(`模型训练失败: ${error.message}`)
        trainingResult.value = {
          success: false,
          error: error.message
        }
      }
    }

    const viewResults = () => {
      currentStep.value = 3
    }

    const resetTraining = () => {
      currentStep.value = 0
      featureFile.value = null
      labelFile.value = null
      uploadedFeatureFile.value = ''
      uploadedLabelFile.value = ''
      training.value = false
      trainingStarted.value = false
      trainingResult.value = null
      featureUploadRef.value?.clearFiles()
      labelUploadRef.value?.clearFiles()
    }

    const goToMonitor = () => {
      router.push('/monitor')
    }

    const metricsTable = computed(() => {
      if (!trainingResult.value || !trainingResult.value.metrics) {
        return []
      }

      const metrics = trainingResult.value.metrics
      const table = []

      if (metrics.accuracy) {
        table.push({
          metric: '准确率 (Accuracy)',
          mean: metrics.accuracy.mean?.toFixed(4) || 'N/A',
          std: metrics.accuracy.std?.toFixed(4) || 'N/A'
        })
      }

      if (metrics.precision) {
        table.push({
          metric: '精确率 (Precision)',
          mean: metrics.precision.mean?.toFixed(4) || 'N/A',
          std: metrics.precision.std?.toFixed(4) || 'N/A'
        })
      }

      if (metrics.recall) {
        table.push({
          metric: '召回率 (Recall)',
          mean: metrics.recall.mean?.toFixed(4) || 'N/A',
          std: metrics.recall.std?.toFixed(4) || 'N/A'
        })
      }

      if (metrics.f1) {
        table.push({
          metric: 'F1分数',
          mean: metrics.f1.mean?.toFixed(4) || 'N/A',
          std: metrics.f1.std?.toFixed(4) || 'N/A'
        })
      }

      if (metrics.roc_auc) {
        table.push({
          metric: 'ROC-AUC',
          mean: metrics.roc_auc.mean?.toFixed(4) || 'N/A',
          std: metrics.roc_auc.std?.toFixed(4) || 'N/A'
        })
      }

      return table
    })

    return {
      currentStep,
      featureUploadRef,
      labelUploadRef,
      featureFile,
      labelFile,
      uploading,
      uploadedFeatureFile,
      uploadedLabelFile,
      trainConfig,
      training,
      trainingStarted,
      trainingResult,
      handleFeatureFileChange,
      handleFeatureFileRemove,
      handleLabelFileChange,
      handleLabelFileRemove,
      formatFileSize,
      uploadFiles,
      getModelTypeName,
      startTraining,
      viewResults,
      resetTraining,
      goToMonitor,
      metricsTable
    }
  }
}
</script>

<style scoped>
.train-model {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.card-header .el-icon {
  margin-right: 8px;
  font-size: 24px;
  color: #409eff;
}

.step-content {
  margin-top: 40px;
  min-height: 400px;
}

.step-panel {
  padding: 20px;
}

.file-info {
  margin-top: 10px;
}

.training-status {
  padding: 40px;
  text-align: center;
}

.training-result {
  padding: 20px;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>

