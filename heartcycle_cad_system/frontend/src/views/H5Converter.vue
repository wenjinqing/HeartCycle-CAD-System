<template>
  <div class="h5-converter-container">
    <el-card class="header-card">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Tools /></el-icon>
            H5文件格式转换
          </span>
          <el-tag type="info" size="small">工具</el-tag>
        </div>
      </template>

      <el-alert
        title="格式转换说明"
        type="info"
        :closable="false"
        class="info-alert"
      >
        <template #default>
          <div class="alert-content">
            <p><strong>为什么需要转换？</strong></p>
            <ul>
              <li>✓ MATLAB格式的H5文件需要转换为标准格式才能训练</li>
              <li>✓ 转换后的文件可以直接用于模型训练，无需额外处理</li>
              <li>✓ 自动合并多个心拍周期，生成完整的ECG数据</li>
            </ul>
            <p class="mt-2"><strong>支持的格式：</strong></p>
            <ul>
              <li>MATLAB格式（measure/value/_XXX结构）→ 自动转换</li>
              <li>标准格式（直接包含ecg数据集）→ 无需转换</li>
            </ul>
          </div>
        </template>
      </el-alert>
    </el-card>

    <!-- 上传区域 -->
    <el-card class="upload-card">
      <template #header>
        <span>步骤1：上传H5文件</span>
      </template>

      <el-upload
        ref="uploadRef"
        drag
        multiple
        :auto-upload="false"
        :file-list="fileList"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        accept=".h5"
        class="upload-demo"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将H5文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持批量上传，只支持.h5文件
          </div>
        </template>
      </el-upload>

      <div class="file-list" v-if="fileList.length > 0">
        <div class="list-header">
          <span>已选择 {{ fileList.length }} 个文件</span>
          <el-button
            type="primary"
            size="small"
            :loading="checking"
            @click="checkFormats"
          >
            <el-icon><Search /></el-icon>
            检查格式
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 格式检查结果 -->
    <el-card class="result-card" v-if="checkResults.length > 0">
      <template #header>
        <span>步骤2：格式检查结果</span>
      </template>

      <el-table :data="checkResults" style="width: 100%">
        <el-table-column prop="fileName" label="文件名" min-width="200" />
        <el-table-column label="格式类型" width="120">
          <template #default="{ row }">
            <el-tag
              :type="row.format === 'simple' ? 'success' : row.format === 'matlab' ? 'warning' : 'danger'"
              size="small"
            >
              {{ formatTypeText(row.format) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="需要转换" width="100">
          <template #default="{ row }">
            <el-icon v-if="row.needs_conversion" color="#E6A23C" :size="20">
              <Warning />
            </el-icon>
            <el-icon v-else color="#67C23A" :size="20">
              <Select />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="200">
          <template #default="{ row }">
            <div class="details">
              <span v-if="row.details.beat_count">
                心拍周期: {{ row.details.beat_count }}
              </span>
              <span v-if="row.details.ecg_size">
                数据点: {{ row.details.ecg_size }}
              </span>
              <span v-if="row.details.structure">
                {{ row.details.structure }}
              </span>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="convert-summary">
        <el-alert
          v-if="needsConversionCount > 0"
          :title="`发现 ${needsConversionCount} 个文件需要转换`"
          type="warning"
          :closable="false"
        >
          <template #default>
            <p>这些文件是MATLAB格式，需要转换后才能用于训练</p>
          </template>
        </el-alert>

        <el-alert
          v-else
          title="所有文件都是标准格式"
          type="success"
          :closable="false"
        >
          <template #default>
            <p>无需转换，可以直接用于模型训练</p>
          </template>
        </el-alert>
      </div>

      <div class="convert-actions">
        <el-button
          type="primary"
          size="large"
          :loading="converting"
          :disabled="needsConversionCount === 0"
          @click="convertFiles"
        >
          <el-icon><Tools /></el-icon>
          开始转换 ({{ needsConversionCount }} 个文件)
        </el-button>

        <el-button
          size="large"
          @click="resetConverter"
        >
          重新选择
        </el-button>
      </div>
    </el-card>

    <!-- 转换结果 -->
    <el-card class="result-card" v-if="convertResult">
      <template #header>
        <span>步骤3：转换结果</span>
      </template>

      <el-result
        :icon="convertResult.success ? 'success' : 'warning'"
        :title="convertResult.message"
      >
        <template #sub-title>
          <div class="statistics">
            <el-statistic title="总计" :value="convertResult.statistics.total" />
            <el-statistic
              title="成功"
              :value="convertResult.statistics.success"
              :value-style="{ color: '#67C23A' }"
            />
            <el-statistic
              title="失败"
              :value="convertResult.statistics.failed"
              :value-style="{ color: '#F56C6C' }"
            />
            <el-statistic
              title="跳过"
              :value="convertResult.statistics.skipped"
              :value-style="{ color: '#909399' }"
            />
          </div>
        </template>

        <template #extra>
          <div class="result-actions">
            <el-button
              type="primary"
              size="large"
              @click="goToTrain"
            >
              <el-icon><Guide /></el-icon>
              前往模型训练
            </el-button>

            <el-button
              size="large"
              @click="resetConverter"
            >
              继续转换其他文件
            </el-button>
          </div>

          <!-- 转换详情 -->
          <div class="converted-files" v-if="convertResult.converted_files.length > 0">
            <el-divider />
            <h4>转换后的文件路径：</h4>
            <el-scrollbar max-height="200px">
              <div
                v-for="(file, index) in convertResult.converted_files"
                :key="index"
                class="file-path-item"
              >
                <el-icon><Document /></el-icon>
                <span>{{ file }}</span>
                <el-button
                  text
                  type="primary"
                  size="small"
                  @click="copyPath(file)"
                >
                  复制
                </el-button>
              </div>
            </el-scrollbar>
          </div>

          <!-- 失败文件 -->
          <div class="failed-files" v-if="convertResult.failed_files.length > 0">
            <el-divider />
            <h4>失败的文件：</h4>
            <el-alert
              v-for="(file, index) in convertResult.failed_files"
              :key="index"
              :title="file"
              type="error"
              :closable="false"
              class="mb-2"
            />
          </div>
        </template>
      </el-result>
    </el-card>

    <!-- 使用指南 -->
    <el-card class="guide-card">
      <template #header>
        <span>使用指南</span>
      </template>

      <el-timeline>
        <el-timeline-item timestamp="步骤1" placement="top">
          <el-card>
            <h4>上传H5文件</h4>
            <p>支持批量上传，可以同时选择多个文件</p>
          </el-card>
        </el-timeline-item>

        <el-timeline-item timestamp="步骤2" placement="top">
          <el-card>
            <h4>检查文件格式</h4>
            <p>系统会自动检测每个文件的格式类型</p>
          </el-card>
        </el-timeline-item>

        <el-timeline-item timestamp="步骤3" placement="top">
          <el-card>
            <h4>转换MATLAB格式</h4>
            <p>对于MATLAB格式的文件，点击"开始转换"按钮</p>
          </el-card>
        </el-timeline-item>

        <el-timeline-item timestamp="步骤4" placement="top">
          <el-card>
            <h4>使用转换后的文件</h4>
            <p>转换成功后，可以直接前往模型训练页面使用这些文件</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Tools,
  UploadFilled,
  Search,
  Warning,
  Select,
  Guide,
  Document
} from '@element-plus/icons-vue'
import apiService from '../services/api'

const router = useRouter()

// 响应式数据
const fileList = ref([])
const checking = ref(false)
const converting = ref(false)
const checkResults = ref([])
const convertResult = ref(null)

// 计算属性
const needsConversionCount = computed(() => {
  return checkResults.value.filter(r => r.needs_conversion).length
})

// 方法
const handleFileChange = (file, files) => {
  fileList.value = files
}

const handleFileRemove = (file, files) => {
  fileList.value = files
  // 清除该文件的检查结果
  checkResults.value = checkResults.value.filter(r => r.fileName !== file.name)
}

const formatTypeText = (format) => {
  const textMap = {
    'simple': '标准格式',
    'matlab': 'MATLAB格式',
    'unknown': '未知格式',
    'error': '读取错误'
  }
  return textMap[format] || format
}

const checkFormats = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  checking.value = true
  checkResults.value = []

  try {
    // 上传文件并检查格式
    for (const file of fileList.value) {
      try {
        // 上传文件
        const uploadResult = await apiService.uploadFile(file.raw)

        if (uploadResult.success) {
          // 检查格式
          const formatResult = await apiService.checkH5Format(uploadResult.file_path)

          checkResults.value.push({
            fileName: file.name,
            filePath: uploadResult.file_path,
            format: formatResult.format_type,
            needs_conversion: formatResult.needs_conversion,
            details: formatResult.details
          })
        }
      } catch (error) {
        console.error(`检查文件 ${file.name} 失败:`, error)
        checkResults.value.push({
          fileName: file.name,
          format: 'error',
          needs_conversion: false,
          details: { error: error.message }
        })
      }
    }

    ElMessage.success('格式检查完成')
  } catch (error) {
    console.error('检查格式失败:', error)
    ElMessage.error('检查格式失败: ' + error.message)
  } finally {
    checking.value = false
  }
}

const convertFiles = async () => {
  const filesToConvert = checkResults.value
    .filter(r => r.needs_conversion)
    .map(r => r.filePath)

  if (filesToConvert.length === 0) {
    ElMessage.info('没有需要转换的文件')
    return
  }

  converting.value = true

  try {
    const result = await apiService.convertH5Files(filesToConvert)
    convertResult.value = result

    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.warning(result.message)
    }
  } catch (error) {
    console.error('转换失败:', error)
    ElMessage.error('转换失败: ' + error.message)
  } finally {
    converting.value = false
  }
}

const copyPath = (path) => {
  navigator.clipboard.writeText(path).then(() => {
    ElMessage.success('路径已复制到剪贴板')
  })
}

const goToTrain = () => {
  router.push('/train-h5-auto')
}

const resetConverter = () => {
  fileList.value = []
  checkResults.value = []
  convertResult.value = null
}
</script>

<style scoped>
.h5-converter-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 500;
}

.header-card,
.upload-card,
.result-card,
.guide-card {
  margin-bottom: 20px;
}

.info-alert {
  margin-top: 10px;
}

.alert-content ul {
  margin: 8px 0;
  padding-left: 20px;
}

.alert-content li {
  margin: 4px 0;
}

.mt-2 {
  margin-top: 8px;
}

.upload-demo {
  margin-bottom: 20px;
}

.file-list {
  margin-top: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #606266;
}

.convert-summary {
  margin: 20px 0;
}

.convert-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

.statistics {
  display: flex;
  gap: 40px;
  justify-content: center;
  margin: 20px 0;
}

.result-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-bottom: 20px;
}

.converted-files,
.failed-files {
  margin-top: 20px;
  text-align: left;
}

.converted-files h4,
.failed-files h4 {
  margin-bottom: 10px;
  color: #303133;
}

.file-path-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  margin: 4px 0;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
}

.file-path-item span {
  flex: 1;
  word-break: break-all;
}

.mb-2 {
  margin-bottom: 8px;
}
</style>
