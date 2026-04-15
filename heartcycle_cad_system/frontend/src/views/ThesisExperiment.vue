<template>
  <div class="experiment-container hc-page-shell">
    <el-card class="header-card hc-card-elevated" shadow="never">
      <div class="header-content">
        <div class="title-section">
          <h1>论文实验系统</h1>
          <p class="subtitle">基于机器学习的冠心病风险预测系统 - 完整实验流程</p>
        </div>
        <el-button type="danger" @click="resetExperiment" :loading="resetting">
          <el-icon><RefreshLeft /></el-icon>
          重置实验
        </el-button>
      </div>
    </el-card>

    <!-- 实验步骤 -->
    <el-card class="steps-card hc-card-elevated" shadow="never">
      <el-steps :active="currentStep" align-center finish-status="success">
        <el-step title="数据预处理" description="KNN插补、异常检测、标准化、SMOTE">
          <template #icon>
            <el-icon><Document /></el-icon>
          </template>
        </el-step>
        <el-step title="特征工程" description="方差阈值、互信息、RFE、特征交叉">
          <template #icon>
            <el-icon><Setting /></el-icon>
          </template>
        </el-step>
        <el-step title="模型训练" description="RF、XGBoost、LightGBM">
          <template #icon>
            <el-icon><Cpu /></el-icon>
          </template>
        </el-step>
        <el-step title="结果分析" description="性能对比、SHAP分析">
          <template #icon>
            <el-icon><TrendCharts /></el-icon>
          </template>
        </el-step>
      </el-steps>
    </el-card>

    <!-- 步骤1: 数据预处理 -->
    <el-card v-if="currentStep === 0" class="content-card hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>步骤1: 数据预处理</span>
          <el-tag type="info">论文第5.2节</el-tag>
        </div>
      </template>

      <el-form :model="preprocessConfig" label-width="150px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="上传数据集">
              <el-upload
                class="upload-demo"
                drag
                :auto-upload="false"
                :on-change="handleFileChange"
                :limit="1"
                accept=".csv"
              >
                <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                <div class="el-upload__text">
                  拖拽文件到此处或 <em>点击上传</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">
                    请上传CSV格式的数据集，必须包含'CAD_risk'列
                  </div>
                </template>
              </el-upload>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="KNN邻居数">
              <el-input-number v-model="preprocessConfig.knn_neighbors" :min="3" :max="10" />
            </el-form-item>
            <el-form-item label="异常比例">
              <el-input-number v-model="preprocessConfig.contamination" :min="0.01" :max="0.1" :step="0.01" />
            </el-form-item>
            <el-form-item label="训练集比例">
              <el-input-number v-model="preprocessConfig.train_size" :min="0.5" :max="0.8" :step="0.05" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button type="primary" @click="runPreprocess" :loading="preprocessing" size="large">
            <el-icon><VideoPlay /></el-icon>
            开始预处理
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 预处理结果 -->
      <div v-if="preprocessResult" class="result-section">
        <el-divider content-position="left">预处理结果</el-divider>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="训练集样本" :value="preprocessResult.train_samples">
              <template #suffix>
                <span class="positive-count">(阳性: {{ preprocessResult.train_positive }})</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="8">
            <el-statistic title="验证集样本" :value="preprocessResult.val_samples">
              <template #suffix>
                <span class="positive-count">(阳性: {{ preprocessResult.val_positive }})</span>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="8">
            <el-statistic title="测试集样本" :value="preprocessResult.test_samples">
              <template #suffix>
                <span class="positive-count">(阳性: {{ preprocessResult.test_positive }})</span>
              </template>
            </el-statistic>
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-top: 20px">
          <el-col :span="6">
            <el-tag :type="preprocessResult.missing_handled ? 'success' : 'info'">
              {{ preprocessResult.missing_handled ? '✓' : '○' }} 缺失值处理
            </el-tag>
          </el-col>
          <el-col :span="6">
            <el-tag :type="preprocessResult.outliers_detected ? 'success' : 'info'">
              {{ preprocessResult.outliers_detected ? '✓' : '○' }} 异常检测
            </el-tag>
          </el-col>
          <el-col :span="6">
            <el-tag :type="preprocessResult.standardized ? 'success' : 'info'">
              {{ preprocessResult.standardized ? '✓' : '○' }} 标准化
            </el-tag>
          </el-col>
          <el-col :span="6">
            <el-tag :type="preprocessResult.balanced ? 'success' : 'info'">
              {{ preprocessResult.balanced ? '✓' : '○' }} 类别平衡
            </el-tag>
          </el-col>
        </el-row>

        <el-button type="success" @click="nextStep" style="margin-top: 20px">
          下一步：特征工程
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </el-card>

    <!-- 步骤2: 特征工程 -->
    <el-card v-if="currentStep === 1" class="content-card hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>步骤2: 特征工程</span>
          <el-tag type="info">论文第5.3节</el-tag>
        </div>
      </template>

      <el-form :model="featureConfig" label-width="150px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="方差阈值">
              <el-input-number v-model="featureConfig.variance_threshold" :min="0.001" :max="0.1" :step="0.001" />
            </el-form-item>
            <el-form-item label="互信息百分比">
              <el-input-number v-model="featureConfig.mi_percentile" :min="0.5" :max="1" :step="0.05" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="RFE特征数">
              <el-input-number v-model="featureConfig.n_features_rfe" :min="20" :max="50" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button type="primary" @click="runFeatureEngineering" :loading="featureEngineering" size="large">
            <el-icon><Tools /></el-icon>
            开始特征工程
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 特征工程结果 -->
      <div v-if="featureResult" class="result-section">
        <el-divider content-position="left">特征工程结果</el-divider>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="原始特征数" :value="featureResult.original_features" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="核心特征数" :value="featureResult.core_features" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="最终特征数" :value="featureResult.final_features" />
          </el-col>
        </el-row>

        <el-timeline style="margin-top: 20px">
          <el-timeline-item
            v-for="(step, index) in featureResult.steps"
            :key="index"
            :timestamp="step.step"
            placement="top"
          >
            特征数: {{ step.n_features }}
          </el-timeline-item>
        </el-timeline>

        <el-button type="success" @click="nextStep" style="margin-top: 20px">
          下一步：模型训练
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </el-card>

    <!-- 步骤3: 模型训练 -->
    <el-card v-if="currentStep === 2" class="content-card hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>步骤3: 模型训练</span>
          <el-tag type="info">论文第5.4-5.5节</el-tag>
        </div>
      </template>

      <el-alert
        title="训练说明"
        type="info"
        description="将训练Random Forest、XGBoost、LightGBM三个模型，并自动选择最佳模型"
        :closable="false"
        style="margin-bottom: 20px"
      />

      <el-button type="primary" @click="runTraining" :loading="training" size="large">
        <el-icon><VideoPlay /></el-icon>
        开始训练模型
      </el-button>

      <!-- 训练结果 -->
      <div v-if="trainingResult" class="result-section">
        <el-divider content-position="left">训练结果</el-divider>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="已训练模型">
            <el-tag v-for="model in trainingResult.models_trained" :key="model" style="margin-right: 5px">
              {{ model }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最佳模型">
            <el-tag type="success">{{ trainingResult.best_model }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最佳AUC">
            <el-statistic :value="trainingResult.best_auc" :precision="4" />
          </el-descriptions-item>
        </el-descriptions>

        <el-button type="success" @click="nextStep" style="margin-top: 20px">
          下一步：结果分析
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </el-card>

    <!-- 步骤4: 结果分析 -->
    <el-card v-if="currentStep === 3" class="content-card hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>步骤4: 结果分析</span>
          <el-tag type="info">论文第5.6节</el-tag>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="性能对比" name="comparison">
          <el-button type="primary" @click="loadResults" :loading="loadingResults">
            <el-icon><Refresh /></el-icon>
            加载结果
          </el-button>

          <div v-if="comparisonTable" style="margin-top: 20px">
            <el-table :data="comparisonTable" border stripe>
              <el-table-column prop="模型" label="模型" width="180" />
              <el-table-column prop="准确率" label="准确率" />
              <el-table-column prop="灵敏度" label="灵敏度" />
              <el-table-column prop="特异性" label="特异性" />
              <el-table-column prop="AUC" label="AUC" />
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="SHAP分析" name="shap">
          <el-button type="primary" @click="loadShapAnalysis" :loading="loadingShap">
            <el-icon><DataAnalysis /></el-icon>
            SHAP分析
          </el-button>

          <div v-if="shapResult" style="margin-top: 20px">
            <el-descriptions title="SHAP分析结果" :column="1" border>
              <el-descriptions-item label="分析模型">
                <el-tag type="success">{{ shapResult.model }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="阳性类概率">
                {{ formatRiskProb(shapResult.sample_explanation?.prediction) }}%
              </el-descriptions-item>
            </el-descriptions>

            <el-divider content-position="left">特征重要性 Top 10</el-divider>
            <el-table :data="shapResult.feature_importance" border stripe>
              <el-table-column prop="feature" label="特征" />
              <el-table-column prop="importance" label="重要性" :formatter="formatNumber" />
              <el-table-column prop="importance_pct" label="占比" :formatter="formatPercent" />
            </el-table>

            <el-divider content-position="left">临床解读</el-divider>
            <el-card class="interpretation-card hc-card-elevated" shadow="never">
              <pre>{{ shapResult.clinical_interpretation }}</pre>
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="下载报告" name="download">
          <el-button type="success" @click="downloadReport" size="large">
            <el-icon><Download /></el-icon>
            下载完整实验报告
          </el-button>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document, Setting, Cpu, TrendCharts, VideoPlay, ArrowRight,
  RefreshLeft, UploadFilled, Tools, Refresh, DataAnalysis, Download
} from '@element-plus/icons-vue'
import { api } from '@/services/api'

const currentStep = ref(0)
const activeTab = ref('comparison')

// 配置
const preprocessConfig = reactive({
  knn_neighbors: 5,
  contamination: 0.05,
  train_size: 0.7,
  val_size: 0.15,
  test_size: 0.15
})

const featureConfig = reactive({
  variance_threshold: 0.01,
  mi_percentile: 0.8,
  n_features_rfe: 38
})

// 状态
const preprocessing = ref(false)
const featureEngineering = ref(false)
const training = ref(false)
const loadingResults = ref(false)
const loadingShap = ref(false)
const resetting = ref(false)

// 结果
const preprocessResult = ref(null)
const featureResult = ref(null)
const trainingResult = ref(null)
const comparisonTable = ref(null)
const shapResult = ref(null)

// 文件
const uploadFile = ref(null)

const handleFileChange = (file) => {
  uploadFile.value = file.raw
}

const runPreprocess = async () => {
  if (!uploadFile.value) {
    ElMessage.warning('请先上传数据集')
    return
  }

  preprocessing.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)

    const response = await api.post('/experiment/preprocess', formData, {
      params: preprocessConfig
    })

    // axios 拦截器已返回 body；兼容未拦截时的 response.data
    preprocessResult.value = response?.data ?? response
    ElMessage.success('数据预处理完成！')
  } catch (error) {
    ElMessage.error('预处理失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    preprocessing.value = false
  }
}

const runFeatureEngineering = async () => {
  featureEngineering.value = true
  try {
    const response = await api.post('/experiment/feature-engineering', featureConfig)
    featureResult.value = response
    ElMessage.success('特征工程完成！')
  } catch (error) {
    ElMessage.error('特征工程失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    featureEngineering.value = false
  }
}

const runTraining = async () => {
  training.value = true
  try {
    const response = await api.post('/experiment/train-models')
    trainingResult.value = response
    ElMessage.success(response.message || '模型训练完成！')
  } catch (error) {
    ElMessage.error('训练失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    training.value = false
  }
}

const loadResults = async () => {
  loadingResults.value = true
  try {
    const response = await api.get('/experiment/results')
    comparisonTable.value = response.comparison_table
    ElMessage.success('结果加载完成！')
  } catch (error) {
    ElMessage.error('加载失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingResults.value = false
  }
}

const loadShapAnalysis = async () => {
  loadingShap.value = true
  try {
    const response = await api.get('/experiment/shap-analysis')
    shapResult.value = response
    ElMessage.success('SHAP分析完成！')
  } catch (error) {
    ElMessage.error('分析失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingShap.value = false
  }
}

const downloadReport = async () => {
  try {
    const response = await api.get('/experiment/download-report', {
      responseType: 'blob'
    })
    const blob = response instanceof Blob ? response : new Blob([response])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'heartcycle_experiment_report.pdf')
    document.body.appendChild(link)
    link.click()
    link.remove()
    ElMessage.success('报告下载成功！')
  } catch (error) {
    ElMessage.error('下载失败: ' + (error.response?.data?.detail || error.message))
  }
}

const resetExperiment = async () => {
  try {
    await ElMessageBox.confirm('确定要重置实验吗？所有数据将被清除。', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    resetting.value = true
    await api.post('/experiment/reset')

    currentStep.value = 0
    preprocessResult.value = null
    featureResult.value = null
    trainingResult.value = null
    comparisonTable.value = null
    shapResult.value = null
    uploadFile.value = null

    ElMessage.success('实验已重置')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重置失败')
    }
  } finally {
    resetting.value = false
  }
}

const nextStep = () => {
  currentStep.value++
}

/** 后端为 [0,1] 概率；旧数据若异常则钳制到 0–100% 展示 */
const formatRiskProb = (p) => {
  const x = Number(p)
  if (Number.isNaN(x)) return '--'
  return (Math.min(1, Math.max(0, x)) * 100).toFixed(2)
}

const formatNumber = (row, column, cellValue) => {
  return cellValue?.toFixed(4) || '-'
}

const formatPercent = (row, column, cellValue) => {
  return cellValue ? `${cellValue.toFixed(2)}%` : '-'
}
</script>

<style scoped>
.experiment-container {
  padding-top: 4px;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section h1 {
  margin: 0;
  font-size: 28px;
  color: #409EFF;
}

.subtitle {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.steps-card {
  margin-bottom: 20px;
}

.content-card {
  margin-bottom: 20px;
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.result-section {
  margin-top: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.positive-count {
  font-size: 12px;
  color: #67C23A;
}

.interpretation-card {
  background: #f9f9f9;
}

.interpretation-card pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  line-height: 1.6;
}

:deep(.el-upload-dragger) {
  padding: 40px;
}

:deep(.el-statistic__content) {
  font-size: 24px;
  font-weight: bold;
}
</style>
