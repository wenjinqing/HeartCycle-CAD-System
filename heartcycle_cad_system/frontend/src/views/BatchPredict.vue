<template>
  <div class="batch-predict">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon><DataAnalysis /></el-icon>
          <span>批量预测</span>
        </div>
      </template>

      <el-alert
        title="使用说明"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        <template #default>
          <p style="margin: 5px 0; font-weight: bold">上传CSV（逗号分隔值）文件进行批量预测，CSV文件应包含以下列：</p>
          <p style="margin: 10px 0 5px 0; font-weight: bold">必需列：</p>
          <ul style="margin: 0 0 10px 20px; padding: 0; line-height: 1.8">
            <li><strong>age（年龄）</strong>：受试者年龄，单位：岁</li>
            <li><strong>gender（性别）</strong>：受试者性别，取值：M（男性）或 F（女性）</li>
            <li><strong>height（身高）</strong>：受试者身高，单位：cm（厘米）</li>
            <li><strong>weight（体重）</strong>：受试者体重，单位：kg（千克）</li>
          </ul>
          <p style="margin: 10px 0 5px 0; font-weight: bold">可选列（HRV（心率变异性）特征，基于ECG（心电图）信号提取）：</p>
          <ul style="margin: 0 0 10px 20px; padding: 0; line-height: 1.8">
            <li><strong>mean_rr（平均RR间期）</strong>：ECG（心电图）信号中连续两个R波之间的平均时间间隔，单位：ms（毫秒），HRV（心率变异性）时域特征</li>
            <li><strong>sdnn（正常RR间期标准差，SDNN）</strong>：Standard Deviation of Normal-to-Normal intervals，正常RR间期的标准差，反映整体心率变异性，单位：ms（毫秒），HRV（心率变异性）时域特征</li>
            <li><strong>rmssd（连续RR间期差值的均方根，RMSSD）</strong>：Root Mean Square of Successive Differences，连续RR间期差值的均方根，主要反映副交感神经活性，单位：ms（毫秒），HRV（心率变异性）时域特征</li>
            <li><strong>pnn50（RR间期差异超过50ms的百分比，pNN50）</strong>：Percentage of NN intervals differing by more than 50ms，相邻RR间期差异超过50ms的百分比，反映心率变异性，单位：%（百分比），HRV（心率变异性）时域特征</li>
            <li><strong>lf_hf_ratio（LF/HF（低频与高频功率比值）比值）</strong>：Low Frequency/High Frequency Ratio，心率变异性频域分析中的低频与高频功率比值，反映自主神经系统的平衡状态，无量纲，HRV（心率变异性）频域特征</li>
            <li><strong>bmi（身体质量指数，BMI）</strong>：Body Mass Index，由身高和体重计算得出，公式：BMI = 体重(kg) / 身高(m)²，单位：kg/m²</li>
          </ul>
          <p style="margin: 10px 0 0 0; color: #909399; font-size: 12px">注意：第一行为列名，后续行为数据。CSV（逗号分隔值）文件应使用UTF-8编码。</p>
        </template>
      </el-alert>

      <el-form :model="form" label-width="140px">
        <el-form-item label="选择模型">
          <el-select
            v-model="form.modelId"
            placeholder="请选择预测模型"
            style="width: 100%"
            :loading="loadingModels"
            filterable
          >
            <el-option
              v-for="model in modelList"
              :key="model.model_id"
              :label="getModelDisplayName(model)"
              :value="model.model_id"
            >
              <div style="display: flex; justify-content: space-between">
                <span>{{ getModelDisplayName(model) }}</span>
                <el-tag :type="getModelTypeTag(model.model_type)" size="small" style="margin-left: 10px">
                  {{ getModelTypeName(model.model_type) }}
                </el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="上传CSV（逗号分隔值）文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :limit="1"
            accept=".csv"
            :disabled="predicting"
          >
            <el-button type="primary" :loading="predicting">
              <el-icon><Upload /></el-icon>
              {{ selectedFile ? '重新选择文件' : '选择CSV文件' }}
            </el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持CSV（逗号分隔值）格式文件，文件大小不超过10MB
              </div>
            </template>
          </el-upload>
          <div v-if="selectedFile" class="file-info">
            <el-tag type="info" style="margin-top: 10px">
              <el-icon><Document /></el-icon>
              {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
            </el-tag>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            @click="startBatchPredict"
            :loading="predicting"
            :disabled="!form.modelId || !selectedFile"
          >
            <el-icon v-if="!predicting"><Search /></el-icon>
            {{ predicting ? '预测中...' : '开始批量预测' }}
          </el-button>
          <el-button size="large" @click="resetForm" :disabled="predicting">
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 预测结果 -->
      <el-card v-if="predictionResults.length > 0" shadow="never" style="margin-top: 24px">
        <template #header>
          <div class="card-header">
            <span style="font-weight: 600">预测结果</span>
            <div style="display: flex; align-items: center; gap: 12px">
              <el-tag type="info" size="default">共 {{ predictionResults.length }} 条</el-tag>
              <el-button
                type="primary"
                size="small"
                @click="exportResults"
              >
                <el-icon><Download /></el-icon>
                导出结果
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          :data="predictionResults"
          style="width: 100%"
          stripe
          border
          :max-height="500"
        >
          <el-table-column type="index" label="序号" width="70" align="center" />
          <el-table-column
            v-for="col in resultColumns"
            :key="col.prop"
            :prop="col.prop"
            :label="col.label"
            :width="col.width"
            :min-width="col.minWidth"
            :formatter="col.formatter"
          />
          <el-table-column prop="prediction" label="预测结果" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="row.prediction === 1 ? 'danger' : 'success'">
                {{ row.prediction === 1 ? '高风险' : '低风险' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="riskScore" label="风险评分" width="120" align="center" sortable>
            <template #default="{ row }">
              <el-tag :type="getRiskType(row.riskScore)">
                {{ row.riskScore }}%
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="confidence" label="置信度" width="100" align="center">
            <template #default="{ row }">
              {{ (row.confidence * 100).toFixed(1) }}%
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  Upload,
  Document,
  Search,
  RefreshLeft,
  Download
} from '@element-plus/icons-vue'
import { apiService } from '../services/api'
import { getColumnLabel } from '../utils/columnDescriptions'

export default {
  name: 'BatchPredict',
  components: {
    DataAnalysis,
    Upload,
    Document,
    Search,
    RefreshLeft,
    Download
  },
  setup() {
    const uploadRef = ref(null)
    const loadingModels = ref(false)
    const modelList = ref([])
    const selectedFile = ref(null)
    const predicting = ref(false)
    const predictionResults = ref([])

    const form = ref({
      modelId: ''
    })

    // 结果表格列定义
    const resultColumns = computed(() => {
      if (predictionResults.value.length === 0) return []
      
      // 动态生成列（基于第一行数据的键）
      const firstRow = predictionResults.value[0]
      const columns = []
      
      // 排除预测相关字段（这些字段单独显示）
      const excludeFields = ['prediction', 'confidence', 'riskScore', 'probability', 'error']
      
      Object.keys(firstRow).forEach(key => {
        if (!excludeFields.includes(key)) {
          columns.push({
            prop: key,
            label: getColumnLabel(key),
            minWidth: 120
          })
        }
      })
      
      return columns
    })

    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    const getRiskType = (score) => {
      const numScore = parseFloat(score)
      if (numScore < 30) return 'success'
      if (numScore < 60) return 'warning'
      return 'danger'
    }

    const getModelDisplayName = (model) => {
      let name = model.model_id || '未知模型'
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
      return name
    }

    const getModelTypeName = (type) => {
      const typeMap = {
        'lr': '逻辑回归',
        'svm': '支持向量机',
        'rf': '随机森林'
      }
      return typeMap[type] || type
    }

    const getModelTypeTag = (type) => {
      const tagMap = {
        'lr': 'info',
        'svm': 'warning',
        'rf': 'success'
      }
      return tagMap[type] || ''
    }

    const handleFileChange = (file) => {
      if (file.raw) {
        selectedFile.value = file.raw
      }
    }

    const handleFileRemove = () => {
      selectedFile.value = null
    }

    const loadModelList = async () => {
      try {
        loadingModels.value = true
        const modelsResponse = await apiService.getModels()
        
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
        
        modelList.value = models
        
        if (models.length > 0 && !form.value.modelId) {
          form.value.modelId = models[0].model_id
        }
      } catch (error) {
        console.error('加载模型列表失败:', error)
        ElMessage.error(`加载模型列表失败: ${error.message}`)
      } finally {
        loadingModels.value = false
      }
    }

    const startBatchPredict = async () => {
      if (!form.value.modelId) {
        ElMessage.warning('请选择预测模型')
        return
      }

      if (!selectedFile.value) {
        ElMessage.warning('请上传CSV（逗号分隔值）文件')
        return
      }

      try {
        predicting.value = true
        ElMessage.info('开始批量预测...')

        // 读取CSV文件
        const text = await selectedFile.value.text()
        const lines = text.split('\n').filter(line => line.trim())
        
        if (lines.length < 2) {
          throw new Error('CSV（逗号分隔值）文件至少需要2行（1行标题 + 1行数据）')
        }

        // 解析CSV（简单解析，假设没有复杂的引号和换行）
        const headers = lines[0].split(',').map(h => h.trim())
        const dataRows = lines.slice(1).map(line => {
          const values = line.split(',').map(v => v.trim())
          const row = {}
          headers.forEach((header, index) => {
            row[header] = values[index] || ''
          })
          return row
        })

        if (dataRows.length === 0) {
          throw new Error('CSV（逗号分隔值）文件没有数据行')
        }

        // 批量预测
        const results = []
        const total = dataRows.length
        
        for (let i = 0; i < dataRows.length; i++) {
          const row = dataRows[i]
          
          // 构建特征向量（根据模型需要的特征）
          // 这里简化处理，实际应该根据模型元数据来确定需要的特征
          const features = [
            parseFloat(row.age) || 0,
            parseFloat(row.gender === 'M' ? 1 : 0) || 0,
            parseFloat(row.height) || 0,
            parseFloat(row.weight) || 0,
            parseFloat(row.mean_rr) || 0,
            parseFloat(row.sdnn) || 0,
            parseFloat(row.rmssd) || 0,
            parseFloat(row.pnn50) || 0,
            parseFloat(row.lf_hf_ratio) || 0
          ]

          try {
            const response = await apiService.predict({
              model_id: form.value.modelId,
              features: features
            })

            const prediction = response.data || response
            
            results.push({
              ...row,
              prediction: prediction.prediction,
              confidence: prediction.confidence || 0,
              probability: prediction.probability || [0, 0],
              riskScore: ((prediction.probability && prediction.probability[1]) ? prediction.probability[1] * 100 : 0).toFixed(1)
            })

            // 显示进度
            if ((i + 1) % 10 === 0 || i + 1 === total) {
              ElMessage.info(`已处理 ${i + 1} / ${total} 条记录`)
            }
          } catch (error) {
            console.error(`第 ${i + 1} 条记录预测失败:`, error)
            // 继续处理下一条
            results.push({
              ...row,
              prediction: -1,
              confidence: 0,
              probability: [0, 0],
              riskScore: 0,
              error: error.message
            })
          }
        }

        predictionResults.value = results
        ElMessage.success(`批量预测完成，共处理 ${results.length} 条记录`)
      } catch (error) {
        console.error('批量预测失败:', error)
        ElMessage.error(`批量预测失败: ${error.message}`)
      } finally {
        predicting.value = false
      }
    }

    const exportResults = () => {
      if (predictionResults.value.length === 0) {
        ElMessage.warning('没有可导出的结果')
        return
      }

      // 构建CSV内容
      const headers = resultColumns.value.map(col => col.label || col.prop)
      headers.push('预测结果', '风险评分', '置信度')

      const rows = predictionResults.value.map(row => {
        const values = resultColumns.value.map(col => {
          const val = row[col.prop]
          return val !== undefined && val !== null ? String(val) : ''
        })
        values.push(
          row.prediction === 1 ? '高风险' : '低风险',
          row.riskScore + '%',
          (row.confidence * 100).toFixed(1) + '%'
        )
        return values.map(v => `"${v}"`).join(',')
      })

      const csvContent = [
        headers.map(h => `"${h}"`).join(','),
        ...rows
      ].join('\n')

      // 添加BOM以支持中文
      const BOM = '\uFEFF'
      const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `批量预测结果_${new Date().getTime()}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      ElMessage.success('结果已导出')
    }

    const resetForm = () => {
      form.value.modelId = ''
      selectedFile.value = null
      predictionResults.value = []
      uploadRef.value?.clearFiles()
    }

    onMounted(() => {
      loadModelList()
    })

    return {
      uploadRef,
      loadingModels,
      modelList,
      selectedFile,
      predicting,
      predictionResults,
      form,
      resultColumns,
      formatFileSize,
      getRiskType,
      getModelDisplayName,
      getModelTypeName,
      getModelTypeTag,
      handleFileChange,
      handleFileRemove,
      loadModelList,
      startBatchPredict,
      exportResults,
      resetForm
    }
  }
}
</script>

<style scoped>
.batch-predict {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.card-header .el-icon {
  margin-right: 10px;
  font-size: 24px;
  color: #409eff;
}

:deep(.el-card) {
  border-radius: 12px;
}

:deep(.el-card__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfc;
}

:deep(.el-alert) {
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

:deep(.el-alert__content) {
  padding: 12px 0;
}

:deep(.el-form) {
  padding: 20px 0;
}

:deep(.el-form-item) {
  margin-bottom: 28px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
  padding-right: 20px;
  line-height: 32px;
}

:deep(.el-form-item__content) {
  line-height: 32px;
}

.file-info {
  margin-top: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table__header) {
  background: #fafbfc;
}

:deep(.el-table th) {
  background: #fafbfc !important;
  font-weight: 600;
  color: #606266;
}

:deep(.el-button) {
  border-radius: 6px;
  font-weight: 500;
}

:deep(.el-input) {
  border-radius: 6px;
}

:deep(.el-select) {
  border-radius: 6px;
}

:deep(.el-upload) {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
  padding: 40px 20px;
}
</style>

