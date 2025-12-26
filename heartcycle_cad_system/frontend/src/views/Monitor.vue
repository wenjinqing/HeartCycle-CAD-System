<template>
  <div class="monitor">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon><MonitorIcon /></el-icon>
          <span>冠心病监测与预警分析</span>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 体征信息输入 -->
        <el-tab-pane label="体征信息" name="info">
          <el-form
            ref="formRef"
            :model="formData"
            :rules="rules"
            label-width="120px"
            class="monitor-form"
          >
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="年龄" prop="age">
                  <el-input-number
                    v-model="formData.age"
                    :min="1"
                    :max="120"
                    placeholder="请输入年龄"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="性别" prop="gender">
                  <el-radio-group v-model="formData.gender">
                    <el-radio value="M">男</el-radio>
                    <el-radio value="F">女</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="身高 (cm)" prop="height">
                  <el-input-number
                    v-model="formData.height"
                    :min="100"
                    :max="250"
                    :precision="1"
                    placeholder="请输入身高"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="体重 (kg)" prop="weight">
                  <el-input-number
                    v-model="formData.weight"
                    :min="20"
                    :max="200"
                    :precision="1"
                    placeholder="请输入体重"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="BMI" prop="bmi">
              <el-input
                v-model="calculatedBMI"
                disabled
                style="width: 300px"
              >
                <template #append>自动计算</template>
              </el-input>
            </el-form-item>

            <el-divider>模型选择</el-divider>

            <el-form-item label="预测模式" prop="predictionMode">
              <el-radio-group v-model="predictionMode" @change="handlePredictionModeChange">
                <el-radio value="single">单个模型</el-radio>
                <el-radio value="ensemble">模型集成</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="predictionMode === 'single'" label="选择模型" prop="selectedModel">
              <el-select
                v-model="selectedModel"
                placeholder="请选择模型"
                filterable
                style="width: 100%"
                :loading="loadingModels"
                @focus="loadModelList"
              >
                <el-option
                  v-for="model in modelList"
                  :key="model.model_id"
                  :label="getModelDisplayName(model)"
                  :value="model.model_id"
                >
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <span>{{ getModelDisplayName(model) }}</span>
                    <el-tag v-if="model.model_type" size="small" :type="getModelTypeTag(model.model_type)">
                      {{ getModelTypeName(model.model_type) }}
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
              <div style="margin-top: 8px">
                <el-button
                  link
                  size="small"
                  @click="loadModelList"
                  :loading="loadingModels"
                  style="padding: 0"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新列表
                </el-button>
              </div>
            </el-form-item>

            <el-form-item v-if="predictionMode === 'ensemble'" label="选择多个模型" prop="selectedModels">
              <el-select
                v-model="selectedModels"
                placeholder="请选择多个模型（至少2个）"
                filterable
                multiple
                style="width: 100%"
                :loading="loadingModels"
                @focus="loadModelList"
              >
                <el-option
                  v-for="model in modelList"
                  :key="model.model_id"
                  :label="getModelDisplayName(model)"
                  :value="model.model_id"
                >
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <span>{{ getModelDisplayName(model) }}</span>
                    <el-tag v-if="model.model_type" size="small" :type="getModelTypeTag(model.model_type)">
                      {{ getModelTypeName(model.model_type) }}
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
              <div style="margin-top: 8px; display: flex; align-items: center; gap: 10px">
                <el-tag type="info" size="small">已选择 {{ selectedModels.length }} 个模型</el-tag>
                <el-button
                  link
                  size="small"
                  @click="loadModelList"
                  :loading="loadingModels"
                  style="padding: 0"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </el-form-item>

            <el-form-item v-if="predictionMode === 'ensemble'" label="集成方法">
              <el-radio-group v-model="ensembleMethod">
                <el-radio value="voting">投票集成（平均概率）</el-radio>
                <el-radio value="weighted">加权平均</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-divider>HRV特征（可选，如有ECG数据）</el-divider>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="平均RR间期 (ms)">
                  <el-input-number
                    v-model="formData.mean_rr"
                    :min="0"
                    :precision="2"
                    placeholder="平均RR间期"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="SDNN (ms)">
                  <el-input-number
                    v-model="formData.sdnn"
                    :min="0"
                    :precision="2"
                    placeholder="SDNN"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="RMSSD (ms)">
                  <el-input-number
                    v-model="formData.rmssd"
                    :min="0"
                    :precision="2"
                    placeholder="RMSSD"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="pNN50 (%)">
                  <el-input-number
                    v-model="formData.pnn50"
                    :min="0"
                    :max="100"
                    :precision="2"
                    placeholder="pNN50"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="LF/HF比值">
                  <el-input-number
                    v-model="formData.lf_hf_ratio"
                    :min="0"
                    :precision="2"
                    placeholder="LF/HF比值"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider>ECG文件上传（自动提取特征）</el-divider>

            <el-form-item label="上传HDF5文件">
              <el-upload
                ref="uploadRef"
                :auto-upload="false"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                :limit="1"
                accept=".h5"
                :disabled="uploading"
              >
                <el-button type="primary" :loading="uploading">
                  <el-icon><Upload /></el-icon>
                  {{ selectedFile ? '重新选择文件' : '选择HDF5文件' }}
                </el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    支持上传HDF5格式的ECG数据文件，上传后将自动提取HRV特征
                  </div>
                </template>
              </el-upload>
              <div v-if="selectedFile" class="file-info">
                <el-tag type="info" style="margin-top: 10px">
                  <el-icon><Document /></el-icon>
                  {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
                </el-tag>
                <el-button 
                  v-if="!uploading" 
                  type="primary" 
                  size="small" 
                  style="margin-left: 10px"
                  @click="handleUploadAndExtract"
                  :loading="extracting"
                >
                  <el-icon v-if="!extracting"><Upload /></el-icon>
                  {{ extracting ? '提取中...' : '提取特征' }}
                </el-button>
              </div>
              <div v-if="extractedFeatures" class="extracted-features">
                <el-alert
                  title="特征提取成功"
                  type="success"
                  :closable="false"
                  show-icon
                  style="margin-top: 10px"
                >
                  <template #default>
                    <p>已成功提取 {{ Object.keys(extractedFeatures).length }} 个HRV特征</p>
                    <el-button type="primary" size="small" @click="applyExtractedFeatures">
                      <el-icon><Check /></el-icon>
                      应用到表单
                    </el-button>
                  </template>
                </el-alert>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" size="large" @click="submitForm" :loading="analyzing">
                <el-icon v-if="!analyzing"><Search /></el-icon>
                {{ analyzing ? '分析中...' : '开始分析' }}
              </el-button>
              <el-button size="large" @click="resetForm">
                <el-icon><RefreshLeft /></el-icon>
                重置表单
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 分析结果 -->
        <el-tab-pane label="分析结果" name="result" :disabled="!hasResult">
          <div v-if="analyzing" class="analyzing">
            <el-result icon="info">
              <template #icon>
                <el-icon class="is-loading" :size="60"><Loading /></el-icon>
              </template>
              <template #title>正在分析中...</template>
              <template #sub-title>请稍候，系统正在处理您的数据</template>
            </el-result>
          </div>

          <div v-else-if="analysisResult" class="result-content">
            <!-- 风险等级 -->
            <el-card class="risk-card" :class="riskClass">
              <div class="risk-header">
                <el-icon :size="40"><Warning /></el-icon>
                <div>
                  <h2>风险评估结果</h2>
                  <p class="risk-level">{{ riskLevel }}</p>
                </div>
              </div>
              <div class="risk-score">
                <span>风险评分: </span>
                <span class="score-value">{{ riskScore }}%</span>
              </div>
            </el-card>

            <!-- 预测详情 -->
            <el-card style="margin-top: 20px">
              <template #header>
                <span>预测详情</span>
                <el-tag v-if="analysisResult.method === 'ensemble'" type="info" style="margin-left: 10px">
                  集成预测（{{ analysisResult.method === 'voting' ? '投票' : '加权平均' }}）
                </el-tag>
              </template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="预测方法">
                  {{ analysisResult.method === 'ensemble' ? '模型集成' : '单个模型' }}
                  <el-tag v-if="analysisResult.method === 'ensemble'" type="info" size="small" style="margin-left: 10px">
                    {{ analysisResult.modelCount }} 个模型
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="预测类别">
                  <el-tag :type="analysisResult.prediction === 1 ? 'danger' : 'success'">
                    {{ analysisResult.prediction === 1 ? '高风险' : '低风险' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="预测置信度">
                  {{ (analysisResult.confidence * 100).toFixed(2) }}%
                </el-descriptions-item>
                <el-descriptions-item v-if="analysisResult.agreement !== undefined" label="模型一致性">
                  {{ (analysisResult.agreement * 100).toFixed(1) }}%
                  <el-tag :type="analysisResult.agreement > 0.8 ? 'success' : (analysisResult.agreement > 0.5 ? 'warning' : 'danger')" size="small" style="margin-left: 10px">
                    {{ analysisResult.agreement > 0.8 ? '高度一致' : (analysisResult.agreement > 0.5 ? '中等一致' : '存在分歧') }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="类别0概率">
                  {{ (analysisResult.probability[0] * 100).toFixed(2) }}%
                </el-descriptions-item>
                <el-descriptions-item label="类别1概率">
                  {{ (analysisResult.probability[1] * 100).toFixed(2) }}%
                </el-descriptions-item>
                <el-descriptions-item v-if="analysisResult.individualPredictions" label="各模型预测" :span="2">
                  <div style="display: flex; gap: 8px; flex-wrap: wrap">
                    <el-tag
                      v-for="(pred, index) in analysisResult.individualPredictions"
                      :key="index"
                      :type="pred === 1 ? 'danger' : 'success'"
                      size="small"
                    >
                      模型{{ index + 1 }}: {{ pred === 1 ? '高风险' : '低风险' }}
                    </el-tag>
                  </div>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>

            <!-- 预警信息 -->
            <el-alert
              v-if="analysisResult.prediction === 1"
              title="风险预警"
              type="warning"
              :closable="false"
              show-icon
              style="margin-top: 20px"
            >
              <template #default>
                <p>检测到冠心病高风险，建议：</p>
                <ul>
                  <li>及时就医，进行专业检查</li>
                  <li>注意饮食，控制血压和血糖</li>
                  <li>适量运动，保持健康生活方式</li>
                  <li>定期复查，持续监测</li>
                </ul>
              </template>
            </el-alert>

            <!-- 特征重要性（如果有SHAP结果） -->
            <el-card v-if="shapResults" style="margin-top: 20px">
              <template #header>
                <span>关键风险因子分析</span>
              </template>
              <div id="shap-chart" style="height: 400px"></div>
            </el-card>
          </div>

          <div v-else class="no-result">
            <el-empty description="暂无分析结果，请先填写信息并进行分析" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Monitor as MonitorIcon, Search, Warning, Upload, Document, Loading, Refresh, RefreshLeft, Check } from '@element-plus/icons-vue'
import { apiService } from '../services/api'
import { storage } from '../utils/storage'
import * as echarts from 'echarts'

export default {
  name: 'Monitor',
  components: {
    MonitorIcon,
    Search,
    Warning,
    Upload,
    Document,
    Loading,
    Refresh,
    RefreshLeft,
    Check
  },
  setup() {
    const formRef = ref(null)
    const uploadRef = ref(null)
    const activeTab = ref('info')
    const analyzing = ref(false)
    const analysisResult = ref(null)
    const shapResults = ref(null)
    const selectedFile = ref(null)
    const uploading = ref(false)
    const extracting = ref(false)
    const extractedFeatures = ref(null)
    const uploadedFilePath = ref(null)
    const selectedModel = ref('')
    const selectedModels = ref([])
    const modelList = ref([])
    const loadingModels = ref(false)
    const predictionMode = ref('single') // 'single' 或 'ensemble'
    const ensembleMethod = ref('voting') // 'voting' 或 'weighted'

    const formData = ref({
      age: null,
      gender: 'M',
      height: null,
      weight: null,
      mean_rr: null,
      sdnn: null,
      rmssd: null,
      pnn50: null,
      lf_hf_ratio: null
    })

    const rules = {
      age: [
        { required: true, message: '请输入年龄', trigger: 'blur' }
      ],
      gender: [
        { required: true, message: '请选择性别', trigger: 'change' }
      ],
      height: [
        { required: true, message: '请输入身高', trigger: 'blur' }
      ],
      weight: [
        { required: true, message: '请输入体重', trigger: 'blur' }
      ]
    }

    const calculatedBMI = computed(() => {
      if (formData.value.height && formData.value.weight) {
        const heightInM = formData.value.height / 100
        return (formData.value.weight / (heightInM * heightInM)).toFixed(2)
      }
      return ''
    })

    const hasResult = computed(() => {
      return analysisResult.value !== null
    })

    const riskScore = computed(() => {
      if (!analysisResult.value) return 0
      return (analysisResult.value.probability[1] * 100).toFixed(1)
    })

    const riskLevel = computed(() => {
      const score = parseFloat(riskScore.value)
      if (score < 30) return '低风险'
      if (score < 60) return '中风险'
      return '高风险'
    })

    const riskClass = computed(() => {
      const score = parseFloat(riskScore.value)
      if (score < 30) return 'risk-low'
      if (score < 60) return 'risk-medium'
      return 'risk-high'
    })

    const handleFileChange = (file) => {
      if (file.raw) {
        selectedFile.value = file.raw
        extractedFeatures.value = null
        uploadedFilePath.value = null
      }
    }

    const handleFileRemove = () => {
      selectedFile.value = null
      extractedFeatures.value = null
      uploadedFilePath.value = null
    }

    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    const handleUploadAndExtract = async () => {
      if (!selectedFile.value) {
        ElMessage.warning('请先选择文件')
        return
      }

      try {
        uploading.value = true
        
        // 1. 上传文件
        ElMessage.info('正在上传文件...')
        const uploadResponse = await apiService.uploadFile(selectedFile.value)
        // 处理不同的响应格式
        const uploadResult = uploadResponse.data || uploadResponse
        uploadedFilePath.value = uploadResult.file_path
        
        ElMessage.success('文件上传成功，开始提取特征...')
        uploading.value = false
        extracting.value = true

        // 2. 提取特征
        const extractResponse = await apiService.extractFeatures({
          file_path: uploadedFilePath.value,
          use_existing_rpeaks: true,
          extract_hrv: true,
          extract_clinical: false
        })

        // 处理不同的响应格式
        const extractResult = extractResponse.data || extractResponse
        const taskId = extractResult.task_id
        if (!taskId) {
          throw new Error('未获取到任务ID')
        }

        // 3. 轮询查询特征提取状态
        let statusResponse = { status: 'pending' }
        let attempts = 0
        const maxAttempts = 60 // 最多等待60秒

        while (statusResponse.status === 'pending' && attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 1000))
          const response = await apiService.getFeatureStatus(taskId)
          statusResponse = response.data || response
          attempts++
          
          if (statusResponse.status === 'processing') {
            ElMessage.info('特征提取中，请稍候...')
          }
        }
        
        const status = statusResponse

        extracting.value = false

        if (status.status === 'completed' && status.result) {
          extractedFeatures.value = status.result
          ElMessage.success('特征提取成功！')
          
          // 自动应用到表单
          applyExtractedFeatures()
        } else if (status.status === 'failed') {
          throw new Error(status.error || '特征提取失败')
        } else {
          throw new Error('特征提取超时')
        }
      } catch (error) {
        uploading.value = false
        extracting.value = false
        ElMessage.error(`操作失败: ${error.message}`)
        console.error('Upload and extract error:', error)
      }
    }

    const applyExtractedFeatures = () => {
      if (!extractedFeatures.value) return

      const features = extractedFeatures.value
      
      // 将提取的特征应用到表单
      if (features.mean_rr !== undefined) formData.value.mean_rr = features.mean_rr
      if (features.sdnn !== undefined) formData.value.sdnn = features.sdnn
      if (features.rmssd !== undefined) formData.value.rmssd = features.rmssd
      if (features.pnn50 !== undefined) formData.value.pnn50 = features.pnn50
      if (features.lf_hf_ratio !== undefined) formData.value.lf_hf_ratio = features.lf_hf_ratio
      
      ElMessage.success('特征已应用到表单')
    }

    const resetForm = () => {
      formRef.value?.resetFields()
      analysisResult.value = null
      shapResults.value = null
      selectedFile.value = null
      extractedFeatures.value = null
      uploadedFilePath.value = null
      uploading.value = false
      extracting.value = false
      uploadRef.value?.clearFiles()
      selectedModel.value = ''
      selectedModels.value = []
      predictionMode.value = 'single'
    }

    const handlePredictionModeChange = (mode) => {
      if (mode === 'single') {
        selectedModels.value = []
      } else {
        selectedModel.value = ''
      }
    }

    const loadModelList = async () => {
      try {
        loadingModels.value = true
        const modelsResponse = await apiService.getModels()
        
        // 处理不同的响应格式
        let models = []
        if (modelsResponse.data && modelsResponse.data.models) {
          models = modelsResponse.data.models
        } else if (modelsResponse.models) {
          models = modelsResponse.models
        } else if (Array.isArray(modelsResponse)) {
          models = modelsResponse
        } else if (modelsResponse.data && Array.isArray(modelsResponse.data)) {
          models = modelsResponse.data
        }
        
        // 按创建时间排序（最新的在前）
        models.sort((a, b) => {
          const timeA = new Date(a.created_at || 0).getTime()
          const timeB = new Date(b.created_at || 0).getTime()
          return timeB - timeA
        })
        
        modelList.value = models
        
        // 如果没有选择模型且列表不为空，自动选择第一个
        if (!selectedModel.value && models.length > 0) {
          selectedModel.value = models[0].model_id
        }
      } catch (error) {
        console.error('加载模型列表失败:', error)
        ElMessage.error(`加载模型列表失败: ${error.message}`)
        modelList.value = []
      } finally {
        loadingModels.value = false
      }
    }

    const getModelDisplayName = (model) => {
      // 生成模型的显示名称
      let name = model.model_id || '未知模型'
      
      // 如果有创建时间，格式化显示
      if (model.created_at) {
        try {
          const date = new Date(model.created_at)
          const timeStr = date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          })
          name = `${name} (${timeStr})`
        } catch (e) {
          // 忽略日期解析错误
        }
      }
      
      // 如果有模型类型，添加到名称中
      if (model.model_type) {
        const typeName = getModelTypeName(model.model_type)
        name = `${name} - ${typeName}`
      }
      
      return name
    }

    const getModelTypeName = (type) => {
      const names = {
        'lr': '逻辑回归',
        'svm': '支持向量机',
        'rf': '随机森林'
      }
      return names[type] || type
    }

    const getModelTypeTag = (type) => {
      const tags = {
        'lr': 'primary',
        'svm': 'success',
        'rf': 'warning'
      }
      return tags[type] || 'info'
    }

    // 组件挂载时加载模型列表
    onMounted(() => {
      loadModelList()
    })

    const handleTabChange = (tabName) => {
      if (tabName === 'result' && !hasResult.value) {
        ElMessage.warning('请先完成分析')
        activeTab.value = 'info'
      }
    }

    const buildFeatureVector = () => {
      // 如果已经提取了完整的特征，优先使用提取的特征
      if (extractedFeatures.value) {
        return buildFeatureVectorFromExtracted(extractedFeatures.value)
      }
      
      // 否则使用表单数据构建基础特征向量（10个特征）
      const features = []
      
      // 临床特征（5个）
      features.push(formData.value.age || 0)
      features.push(formData.value.gender === 'M' ? 1 : 0)
      features.push(formData.value.height || 0)
      features.push(formData.value.weight || 0)
      features.push(parseFloat(calculatedBMI.value) || 0)
      
      // HRV基础特征（5个）
      features.push(formData.value.mean_rr || 0)
      features.push(formData.value.sdnn || 0)
      features.push(formData.value.rmssd || 0)
      features.push(formData.value.pnn50 || 0)
      features.push(formData.value.lf_hf_ratio || 0)
      
      return features
    }

    const buildFeatureVectorFromExtracted = (extracted) => {
      // 从提取的特征字典构建特征向量
      // 特征顺序需要与训练时的特征顺序一致
      const features = []
      
      // 临床特征（5个）
      features.push(extracted.age || extracted.height_cm || formData.value.age || 0)
      features.push(extracted.gender_male !== undefined ? extracted.gender_male : (formData.value.gender === 'M' ? 1 : 0))
      features.push(extracted.height_cm || formData.value.height || 0)
      features.push(extracted.weight_kg || formData.value.weight || 0)
      features.push(extracted.bmi || parseFloat(calculatedBMI.value) || 0)
      
      // HRV时域特征（优先使用提取的，否则使用表单值）
      features.push(extracted.mean_rr || formData.value.mean_rr || 0)
      features.push(extracted.sdnn || extracted.std_rr || formData.value.sdnn || 0)
      features.push(extracted.rmssd || formData.value.rmssd || 0)
      features.push(extracted.pnn50 || formData.value.pnn50 || 0)
      
      // HRV频域特征
      features.push(extracted.lf_hf_ratio || formData.value.lf_hf_ratio || 0)
      
      // 如果有更多特征，添加进去（保持向后兼容）
      // 时域特征
      if (extracted.min_rr !== undefined) features.push(extracted.min_rr)
      if (extracted.max_rr !== undefined) features.push(extracted.max_rr)
      if (extracted.median_rr !== undefined) features.push(extracted.median_rr)
      if (extracted.sdsd !== undefined) features.push(extracted.sdsd)
      if (extracted.mean_hr !== undefined) features.push(extracted.mean_hr)
      
      // 频域特征
      if (extracted.total_power !== undefined) features.push(extracted.total_power)
      if (extracted.vlf_power !== undefined) features.push(extracted.vlf_power)
      if (extracted.lf_power !== undefined) features.push(extracted.lf_power)
      if (extracted.hf_power !== undefined) features.push(extracted.hf_power)
      
      // 非线性特征
      if (extracted.sd1 !== undefined) features.push(extracted.sd1)
      if (extracted.sd2 !== undefined) features.push(extracted.sd2)
      if (extracted.sd1_sd2_ratio !== undefined) features.push(extracted.sd1_sd2_ratio)
      if (extracted.sample_entropy !== undefined) features.push(extracted.sample_entropy)
      if (extracted.approximate_entropy !== undefined) features.push(extracted.approximate_entropy)
      
      return features
    }

    const submitForm = async () => {
      if (!formRef.value) return
      
      try {
        await formRef.value.validate()
        
        analyzing.value = true
        activeTab.value = 'result'
        
        // 如果上传了文件但还没有提取特征，先提取
        if (selectedFile.value && !extractedFeatures.value) {
          ElMessage.info('正在提取特征...')
          await handleUploadAndExtract()
          if (!extractedFeatures.value) {
            throw new Error('特征提取失败，无法继续预测')
          }
          ElMessage.success('特征提取完成')
        }
        
        // 构建特征向量
        const features = buildFeatureVector()
        console.log('构建的特征向量:', features, '特征数量:', features.length)
        
        // 根据预测模式选择使用单个模型还是集成模型
        let predictionResponse
        
        if (predictionMode.value === 'ensemble') {
          // 集成预测
          if (!selectedModels.value || selectedModels.value.length < 2) {
            throw new Error('集成预测需要选择至少2个模型')
          }
          
          console.log('使用集成预测:', { modelIds: selectedModels.value, method: ensembleMethod.value, featuresCount: features.length })
          
          predictionResponse = await apiService.predictEnsemble({
            model_ids: selectedModels.value,
            features: features,
            method: ensembleMethod.value
          })
        } else {
          // 单个模型预测
          let modelId = selectedModel.value
          if (!modelId) {
            // 如果没有选择模型，尝试获取模型列表并选择第一个
            const modelsResponse = await apiService.getModels()
            console.log('模型列表响应:', modelsResponse)
            
            // 处理不同的响应格式
            let availableModels = []
            if (modelsResponse.data && modelsResponse.data.models) {
              availableModels = modelsResponse.data.models
            } else if (modelsResponse.models) {
              availableModels = modelsResponse.models
            } else if (Array.isArray(modelsResponse)) {
              availableModels = modelsResponse
            } else if (modelsResponse.data && Array.isArray(modelsResponse.data)) {
              availableModels = modelsResponse.data
            }
            
            if (!availableModels || availableModels.length === 0) {
              throw new Error('没有可用的模型，请先训练模型。可以在"模型训练"页面训练模型。')
            }
            
            modelId = availableModels[0].model_id
            selectedModel.value = modelId // 自动选择第一个模型
            console.log('自动选择模型:', modelId)
          } else {
            console.log('使用选择的模型:', modelId)
          }
          
          // 进行预测
          console.log('发送预测请求:', { modelId, featuresCount: features.length })
          predictionResponse = await apiService.predict({
            model_id: modelId,
            features: features
          })
        }
        
        console.log('预测响应:', predictionResponse)
        
        // 处理不同的响应格式
        let prediction = predictionResponse
        if (predictionResponse.data) {
          prediction = predictionResponse.data
        } else if (predictionResponse.prediction !== undefined) {
          prediction = predictionResponse
        }
        
        analysisResult.value = {
          prediction: prediction.prediction,
          probability: prediction.probability || [0.5, 0.5],
          confidence: prediction.confidence || 0.5,
          method: prediction.method || 'single',
          modelCount: prediction.model_count || 1,
          modelIds: prediction.model_ids || [selectedModel.value],
          agreement: prediction.agreement, // 投票一致性
          individualPredictions: prediction.individual_predictions // 各模型预测结果
        }
        
        // 尝试获取SHAP分析结果（只对单个模型）
        if (predictionMode.value === 'single') {
          const modelId = selectedModel.value || (prediction.model_ids && prediction.model_ids[0])
          if (modelId) {
            try {
              const shapData = await apiService.getSHAPResults(modelId)
              if (shapData && shapData.feature_importance) {
                shapResults.value = shapData
                // 渲染SHAP图表
                setTimeout(() => {
                  renderSHAPChart(shapData)
                }, 100)
              }
            } catch (error) {
              console.warn('SHAP分析不可用:', error)
            }
          }
        }
        
        ElMessage.success('分析完成')
        
        // 保存到历史记录
        try {
          const recordId = storage.saveHistory({
            ...formData.value,
            bmi: parseFloat(calculatedBMI.value) || 0,
            riskScore: parseFloat(riskScore.value),
            prediction: analysisResult.value.prediction,
            probability: analysisResult.value.probability,
            confidence: analysisResult.value.confidence,
            method: analysisResult.value.method || 'single',
            modelId: predictionMode.value === 'single' ? selectedModel.value : null,
            modelIds: predictionMode.value === 'ensemble' ? selectedModels.value : null,
            modelCount: analysisResult.value.modelCount || 1,
            features: features // 保存使用的特征向量
          })
          if (recordId) {
            console.log('历史记录已保存，ID:', recordId)
          }
        } catch (error) {
          console.warn('保存历史记录失败:', error)
        }
      } catch (error) {
        ElMessage.error(`分析失败: ${error.message}`)
        activeTab.value = 'info'
      } finally {
        analyzing.value = false
      }
    }

    const renderSHAPChart = (shapData) => {
      const chartDom = document.getElementById('shap-chart')
      if (!chartDom) return
      
      const myChart = echarts.init(chartDom)
      
      // 准备数据
      const featureNames = Object.keys(shapData.feature_importance)
      const values = Object.values(shapData.feature_importance)
      
      // 排序
      const sorted = featureNames
        .map((name, index) => ({ name, value: values[index] }))
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
        .slice(0, 10) // 只显示前10个
      
      const option = {
        title: {
          text: 'Top 10 关键风险因子',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'value'
        },
        yAxis: {
          type: 'category',
          data: sorted.map(item => item.name)
        },
        series: [
          {
            name: '重要性',
            type: 'bar',
            data: sorted.map(item => item.value),
            itemStyle: {
              color: function(params) {
                return params.value > 0 ? '#f56c6c' : '#67c23a'
              }
            }
          }
        ]
      }
      
      myChart.setOption(option)
    }

    return {
      formRef,
      selectedModel,
      selectedModels,
      modelList,
      loadingModels,
      loadModelList,
      getModelDisplayName,
      getModelTypeName,
      getModelTypeTag,
      predictionMode,
      ensembleMethod,
      handlePredictionModeChange,
      uploadRef,
      activeTab,
      analyzing,
      analysisResult,
      shapResults,
      formData,
      rules,
      calculatedBMI,
      hasResult,
      riskScore,
      riskLevel,
      riskClass,
      handleFileChange,
      handleFileRemove,
      handleUploadAndExtract,
      applyExtractedFeatures,
      formatFileSize,
      resetForm,
      handleTabChange,
      submitForm,
      uploading,
      extracting,
      extractedFeatures,
      selectedFile,
      Refresh,
      RefreshLeft,
      Check
    }
  }
}
</script>

<style scoped>
.monitor {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.card-header .el-icon {
  margin-right: 10px;
  font-size: 24px;
  color: #409eff;
}

.monitor-form {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 0;
}

.analyzing {
  padding: 40px;
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

.result-content {
  padding: 20px;
}

.risk-card {
  text-align: center;
  padding: 30px;
}

.risk-card.risk-low {
  background: #f0f9ff;
  border-color: #67c23a;
}

.risk-card.risk-medium {
  background: #fef0f0;
  border-color: #e6a23c;
}

.risk-card.risk-high {
  background: #fef0f0;
  border-color: #f56c6c;
}

.risk-header {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.risk-header .el-icon {
  margin-right: 15px;
  color: #409eff;
}

.risk-header h2 {
  margin: 0;
  font-size: 24px;
}

.risk-level {
  font-size: 32px;
  font-weight: bold;
  margin: 10px 0;
  color: #409eff;
}

.risk-score {
  font-size: 18px;
  margin-top: 20px;
}

.score-value {
  font-size: 36px;
  font-weight: bold;
  color: #f56c6c;
  margin-left: 10px;
}

.no-result {
  padding: 60px;
  text-align: center;
}

.file-info {
  margin-top: 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.extracted-features {
  margin-top: 10px;
}
</style>

