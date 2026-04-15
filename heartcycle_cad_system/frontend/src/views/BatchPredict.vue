<template>
  <div class="batch-predict hc-page-shell">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon><DataAnalysis /></el-icon>
          <span>批量预测</span>
        </div>
      </template>

      <el-collapse v-model="helpActiveNames" class="batch-help-collapse">
        <el-collapse-item title="使用说明：必需列与文件格式" name="req">
          <p class="batch-help-lead">
            上传 UTF-8 编码的 CSV，首行为列名。gender 可用 M/F 或 0/1；论文数据集可用 gender_male（0/1）、height_cm、weight_kg、sbp/dbp 等列名。
            若模型元数据中有特征列名且与 CSV 表头匹配度较高，将<strong>按训练列顺序</strong>自动对齐（与仅用「监测模板」十维拼扩展相比更准确）。
            标签列（如 CAD_risk）仅用于您自己对答案，不参与推理。
          </p>
          <p class="batch-help-subtitle">必需列</p>
          <ul class="hc-help-list">
            <li><strong>age</strong>：年龄（岁）</li>
            <li><strong>gender</strong>：M / F 或 1 / 0（男/女）</li>
            <li><strong>height</strong>：身高（cm）</li>
            <li><strong>weight</strong>：体重（kg）</li>
          </ul>
        </el-collapse-item>
        <el-collapse-item title="可选：HRV 与 BMI" name="hrv">
          <ul class="hc-help-list">
            <li><strong>mean_rr</strong>：平均 RR 间期（ms）</li>
            <li><strong>sdnn</strong>：正常 RR 间期标准差（ms）</li>
            <li><strong>rmssd</strong>：连续 RR 差值均方根（ms）</li>
            <li><strong>pnn50</strong>：相邻 RR 差 &gt;50ms 占比（%）</li>
            <li><strong>lf_hf_ratio</strong>：低频/高频功率比</li>
            <li><strong>bmi</strong>：可填；缺省时由身高、体重自动计算</li>
          </ul>
        </el-collapse-item>
        <el-collapse-item title="可选：体征、实验室与危险因素（与监测页一致）" name="clinical">
          <ul class="hc-help-list">
            <li>血压/体征：blood_pressure_systolic / diastolic（别名 bp_sys、bp_dia）、resting_heart_rate（resting_hr）、waist_cm</li>
            <li>实验室：total_cholesterol（tc）、ldl、hdl、triglyceride（tg）、fasting_glucose（fpg）、hba1c</li>
            <li>吸烟/活动：smoke_status（never/former/current）、physical_activity（unknown/sedentary/light/moderate/heavy）</li>
            <li>危险因素（0/1）：diabetes、hypertension_dx（hypertension）、dyslipidemia、family_history_cad、chest_pain_symptom</li>
          </ul>
          <p class="hc-help-footnote">未填可选列时按 0、never、unknown 处理，与单次监测逻辑一致。</p>
        </el-collapse-item>
      </el-collapse>

      <el-form :model="form" label-width="140px" class="batch-form-block">
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
          <div class="batch-upload-zone">
            <el-upload
              ref="uploadRef"
              class="batch-upload-inner"
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :limit="1"
              accept=".csv"
              :disabled="predicting"
            >
              <el-button type="primary" :loading="predicting">
                <el-icon><Upload /></el-icon>
                {{ selectedFile ? '重新选择文件' : '选择 CSV 文件' }}
              </el-button>
              <template #tip>
                <div class="el-upload__tip batch-upload-tip">
                  支持逗号分隔、引号包裹字段；单文件不超过 10MB
                </div>
              </template>
            </el-upload>
            <div v-if="selectedFile" class="file-info">
              <el-tag type="success" effect="light" round>
                <el-icon><Document /></el-icon>
                {{ selectedFile.name }}（{{ formatFileSize(selectedFile.size) }}）
              </el-tag>
            </div>
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

        <div v-if="predicting" class="batch-progress-wrap" aria-live="polite">
          <el-progress :percentage="batchProgressPercent" :stroke-width="14" />
          <p class="batch-progress-text">{{ batchProgressLabel }}</p>
        </div>
      </el-form>

      <!-- 预测结果 -->
      <el-card
        v-if="predictionResults.length > 0"
        class="hc-card-elevated batch-results-card"
        shadow="never"
      >
        <template #header>
          <div class="card-header card-header--split">
            <span class="results-title">预测结果</span>
            <div class="results-actions">
              <el-tag type="info" effect="plain" round>共 {{ predictionResults.length }} 条</el-tag>
              <el-button type="primary" size="small" @click="exportResults">
                <el-icon><Download /></el-icon>
                导出 CSV
              </el-button>
            </div>
          </div>
        </template>

        <el-alert
          v-if="suspicionAlert"
          type="warning"
          :closable="false"
          show-icon
          class="batch-suspicion-alert"
          :title="suspicionAlert.title"
          :description="suspicionAlert.description"
        />

        <div v-if="resultStats" class="batch-result-stats">
          <div class="batch-threshold-panel">
            <div class="batch-threshold-head">
              <span class="batch-threshold-title">高风险判定阈值（正类概率 P(y=1)）</span>
              <el-tag type="info" size="small" effect="plain">τ = {{ riskThreshold.toFixed(2) }}</el-tag>
            </div>
            <el-slider
              v-model="riskThreshold"
              :min="0.35"
              :max="0.95"
              :step="0.01"
              :marks="thresholdMarks"
              :format-tooltip="(v) => `${(v * 100).toFixed(0)}%`"
            />
            <p class="batch-threshold-hint">
              默认 0.5 与 sklearn 二分类一致。若 SMOTE 训练后概率整体偏高，可适当<strong>提高 τ</strong> 再观察分布；这不改变模型文件，只影响本页展示与导出中的「档位」列。
            </p>
          </div>

          <div class="batch-stats-grid">
            <div class="batch-stat-card">
              <span class="batch-stat-label">总条数</span>
              <span class="batch-stat-value">{{ resultStats.total }}</span>
            </div>
            <div class="batch-stat-card batch-stat-card--danger">
              <span class="batch-stat-label">高风险（P(1)≥τ）</span>
              <span class="batch-stat-value">{{ resultStats.highRisk }}</span>
              <span class="batch-stat-pct">{{ resultStats.highPctText }}</span>
            </div>
            <div class="batch-stat-card batch-stat-card--success">
              <span class="batch-stat-label">低风险（P(1)&lt;τ）</span>
              <span class="batch-stat-value">{{ resultStats.lowRisk }}</span>
              <span class="batch-stat-pct">{{ resultStats.lowPctText }}</span>
            </div>
            <div v-if="resultStats.failed > 0" class="batch-stat-card batch-stat-card--muted">
              <span class="batch-stat-label">失败</span>
              <span class="batch-stat-value">{{ resultStats.failed }}</span>
            </div>
            <div class="batch-stat-card batch-stat-card--wide">
              <span class="batch-stat-label">风险评分（正类概率×100）</span>
              <span class="batch-stat-line">
                平均 <strong>{{ resultStats.avgRiskText }}</strong>
                · 最低 {{ resultStats.minRiskText }}
                · 最高 {{ resultStats.maxRiskText }}
              </span>
            </div>
          </div>
          <p v-if="resultStats.rawMismatchNote" class="batch-raw-api-note">{{ resultStats.rawMismatchNote }}</p>
          <div class="batch-outcome-bar-wrap">
            <div class="batch-outcome-bar" :title="`高风险 ${resultStats.highPctText} · 低风险 ${resultStats.lowPctText}`">
              <div
                class="batch-outcome-seg batch-outcome-seg--high"
                :style="{ width: resultStats.highBarPct + '%' }"
              />
              <div
                class="batch-outcome-seg batch-outcome-seg--low"
                :style="{ width: resultStats.lowBarPct + '%' }"
              />
            </div>
            <div class="batch-outcome-legend">
              <span><span class="dot dot--high" aria-hidden="true" />高风险 {{ resultStats.highPctText }}</span>
              <span><span class="dot dot--low" aria-hidden="true" />低风险 {{ resultStats.lowPctText }}</span>
            </div>
          </div>
          <div v-if="resultStats.labelCompare" class="batch-label-compare">
            <span class="batch-label-compare-title">与 CSV 标签列对比（不参与推理，仅统计）</span>
            <span class="batch-label-compare-body">
              含标签行 {{ resultStats.labelCompare.labeled }} ·
              标签阳性 {{ resultStats.labelCompare.positive }}（{{ resultStats.labelCompare.positivePct }}）
              · 可比对行 {{ resultStats.labelCompare.comparable }} ·
              展示档位与标签一致 {{ resultStats.labelCompare.agree }}（{{ resultStats.labelCompare.agreePct }}）
            </span>
          </div>
        </div>

        <el-table
          :data="pagedResults"
          class="batch-result-table"
          style="width: 100%"
          stripe
          :max-height="520"
        >
          <el-table-column type="index" :index="resultIndexMethod" label="序号" width="80" align="center" />
          <el-table-column
            v-for="col in resultColumns"
            :key="col.prop"
            :prop="col.prop"
            :label="col.label"
            :width="col.width"
            :min-width="col.minWidth"
            :formatter="col.formatter"
          />
          <el-table-column label="风险档位" width="130" align="center">
            <template #default="{ row }">
              <el-tooltip
                v-if="displayPred(row) !== row.prediction && (row.prediction === 0 || row.prediction === 1)"
                placement="top"
                :content="`模型 API 类别: ${row.prediction === 1 ? '1 高风险' : '0 低风险'}；正类概率 ${(positiveProb(row) * 100).toFixed(1)}%`"
              >
                <el-tag :type="displayPred(row) === 1 ? 'danger' : 'success'">
                  {{ displayPred(row) === 1 ? '高风险' : '低风险' }}
                </el-tag>
              </el-tooltip>
              <el-tag
                v-else
                :type="displayPred(row) === 1 ? 'danger' : displayPred(row) === 0 ? 'success' : 'info'"
              >
                {{
                  displayPred(row) === 1 ? '高风险' : displayPred(row) === 0 ? '低风险' : '失败'
                }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="prediction" label="API类别" width="88" align="center">
            <template #default="{ row }">
              <span v-if="row.prediction === 0 || row.prediction === 1" class="batch-api-pred">{{ row.prediction }}</span>
              <span v-else class="batch-api-pred">—</span>
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
        <div class="batch-result-pagination">
          <el-pagination
            v-model:current-page="resultPage"
            v-model:page-size="resultPageSize"
            :page-sizes="[20, 50, 100, 200]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="predictionResults.length"
            background
            @size-change="onResultPageSizeChange"
          />
        </div>
      </el-card>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick } from 'vue'
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
import {
  appendExtendedClinicalFeaturesFromForm,
  extendedFieldsFromCsvRow,
  featureVectorFromModelColumnNames
} from '../utils/clinicalFeatureVector'
import { parseCsvText, escapeCsvField } from '../utils/csvUtils'

/** 与后端 BatchPredictRequest.max_length 对齐，单次请求行数 */
const PREDICT_BATCH_CHUNK = 2000

const THRESHOLD_SLIDER_MARKS = {
  0.5: '0.5',
  0.65: '0.65',
  0.8: '0.8',
  0.9: '0.9'
}

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
    const batchProgressPercent = ref(0)
    const batchProgressLabel = ref('')
    const resultPage = ref(1)
    const resultPageSize = ref(50)
    /** 二分类高风险判定：正类概率 ≥ τ（缓解 SMOTE+RF 概率整体偏高时的「全员高风险」观感） */
    const riskThreshold = ref(0.5)
    const thresholdMarks = THRESHOLD_SLIDER_MARKS

    const form = ref({
      modelId: ''
    })

    const helpActiveNames = ref(['req'])

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

    const pagedResults = computed(() => {
      const list = predictionResults.value
      if (!list.length) return []
      const start = (resultPage.value - 1) * resultPageSize.value
      return list.slice(start, start + resultPageSize.value)
    })

    const resultIndexMethod = (index) => {
      return (resultPage.value - 1) * resultPageSize.value + index + 1
    }

    const onResultPageSizeChange = () => {
      resultPage.value = 1
    }

    const parseOptionalLabel01 = (row) => {
      const raw =
        row.CAD_risk ??
        row.cad_risk ??
        row.label ??
        row.target ??
        row.y
      if (raw === undefined || raw === null || String(raw).trim() === '') return null
      const n = parseFloat(String(raw).replace(',', '.'))
      if (!Number.isFinite(n)) return null
      return n >= 0.5 ? 1 : 0
    }

    const positiveProb = (row) => {
      const pr = row.probability
      if (Array.isArray(pr) && pr.length >= 2) {
        const x = parseFloat(pr[1])
        if (Number.isFinite(x)) return Math.min(1, Math.max(0, x))
      }
      const rs = parseFloat(row.riskScore)
      if (Number.isFinite(rs)) return Math.min(1, Math.max(0, rs / 100))
      return 0
    }

    const displayPred = (row) => {
      const api = row.prediction
      if (api !== 0 && api !== 1) return api
      return positiveProb(row) >= riskThreshold.value ? 1 : 0
    }

    const resultStats = computed(() => {
      const rows = predictionResults.value
      const n = rows.length
      if (!n) return null
      const t = riskThreshold.value
      let highRisk = 0
      let lowRisk = 0
      let failed = 0
      let rawHigh = 0
      let rawLow = 0
      const scores = []
      let labeled = 0
      let positive = 0
      let agree = 0
      let comparable = 0
      for (const r of rows) {
        const api = r.prediction
        if (api === 1) rawHigh += 1
        else if (api === 0) rawLow += 1

        const d = displayPred(r)
        if (d === 1) highRisk += 1
        else if (d === 0) lowRisk += 1
        else failed += 1

        const rs = parseFloat(r.riskScore)
        if (Number.isFinite(rs)) scores.push(rs)
        const y = parseOptionalLabel01(r)
        if (y !== null) {
          labeled += 1
          if (y === 1) positive += 1
          if (d === 0 || d === 1) {
            comparable += 1
            if (d === y) agree += 1
          }
        }
      }
      const denom = Math.max(1, n - failed)
      const highPct = ((highRisk / denom) * 100).toFixed(1)
      const lowPct = ((lowRisk / denom) * 100).toFixed(1)
      const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null
      const minS = scores.length ? Math.min(...scores) : null
      const maxS = scores.length ? Math.max(...scores) : null
      const fmt = (x) => (x === null || !Number.isFinite(x) ? '—' : x.toFixed(1))
      const labelCompare =
        labeled > 0
          ? {
              labeled,
              positive,
              positivePct: ((positive / labeled) * 100).toFixed(1),
              agree,
              comparable,
              agreePct: comparable ? ((agree / comparable) * 100).toFixed(1) : '—'
            }
          : null
      const rawMismatchNote =
        Math.abs(t - 0.5) > 0.001 || rawHigh !== highRisk || rawLow !== lowRisk
          ? `模型 API 输出（sklearn 类别，等价于 P(1)≥0.5）：高风险 ${rawHigh} 条、低风险 ${rawLow} 条。上表统计与柱状图按当前 τ=${t.toFixed(2)} 对正类概率重划分。`
          : ''
      return {
        total: n,
        highRisk,
        lowRisk,
        failed,
        highPctText: `${highPct}%`,
        lowPctText: `${lowPct}%`,
        highBarPct: denom ? (highRisk / denom) * 100 : 0,
        lowBarPct: denom ? (lowRisk / denom) * 100 : 0,
        avgRiskText: fmt(avg),
        minRiskText: fmt(minS),
        maxRiskText: fmt(maxS),
        labelCompare,
        rawMismatchNote
      }
    })

    const suspicionAlert = computed(() => {
      const rows = predictionResults.value
      if (rows.length < 100) return null
      const lc = resultStats.value?.labelCompare
      if (!lc) return null
      const rawHigh = rows.filter((r) => r.prediction === 1).length
      const rate = rawHigh / rows.length
      const posRate = parseFloat(lc.positivePct) / 100
      if (rate > 0.92 && posRate < 0.42 && posRate > 0.01) {
        return {
          title: '几乎全部被判为高风险，与 CSV 中标签阳性比例不一致',
          description:
            '您的数据中「真阳性」约 ' +
            lc.positivePct +
            '%，而模型在 0.5 阈值下几乎全员为高风险，且平均正类概率约 ' +
            (resultStats.value?.avgRiskText || '—') +
            '%。这在用 SMOTE 不平衡处理 + 随机森林时较常见：验证集 AUC 可能尚可，但概率刻度偏乐观。建议在论文中明确工作阈值（拖动下方滑块）、做概率校准（Platt/Isotonic），或对比未做 SMOTE 的模型；并查看「展示档位与标签一致率」是否随 τ 提高而改善。'
        }
      }
      return null
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

    const parseGenderFromRow = (row) => {
      const gm = row.gender_male
      if (gm !== null && gm !== undefined && String(gm).trim() !== '') {
        const n = parseFloat(gm)
        if (n === 1) return 1
        if (n === 0) return 0
      }
      const v = row.gender
      if (v === null || v === undefined || v === '') return 0
      const s = String(v).trim().toUpperCase()
      if (s === 'M' || s === 'MALE' || s === '男') return 1
      if (s === 'F' || s === 'FEMALE' || s === '女') return 0
      const n = parseFloat(s)
      if (n === 1) return 1
      if (n === 0) return 0
      return 0
    }

    const rowToFeatureVector = (row) => {
      const h = parseFloat(row.height ?? row.height_cm) || 0
      const w = parseFloat(row.weight ?? row.weight_kg) || 0
      const bmiCol = parseFloat(row.bmi)
      const bmiVal = Number.isFinite(bmiCol) && bmiCol > 0 ? bmiCol : (h > 0 && w > 0 ? w / ((h / 100) ** 2) : 0)
      const hr = parseFloat(row.heart_rate ?? row.resting_hr ?? row.resting_heart_rate) || 0
      const meanRrCol = parseFloat(row.mean_rr)
      const meanRr =
        Number.isFinite(meanRrCol) && meanRrCol > 0 ? meanRrCol : (hr > 0 ? 60000 / hr : 0)
      const features = [
        parseFloat(row.age) || 0,
        parseGenderFromRow(row),
        h,
        w,
        bmiVal,
        meanRr,
        parseFloat(row.sdnn) || 0,
        parseFloat(row.rmssd) || 0,
        parseFloat(row.pnn50) || 0,
        parseFloat(row.lf_hf_ratio) || 0
      ]
      appendExtendedClinicalFeaturesFromForm(features, extendedFieldsFromCsvRow(row))
      return features
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
        batchProgressPercent.value = 0
        batchProgressLabel.value = '正在解析 CSV…'

        const text = await selectedFile.value.text()
        const { headers, rows: dataRows } = parseCsvText(text)

        if (headers.length === 0 || dataRows.length === 0) {
          throw new Error('CSV（逗号分隔值）文件至少需要2行（1行标题 + 1行数据）')
        }

        const total = dataRows.length
        batchProgressLabel.value = `正在准备 ${total} 条特征…`
        await nextTick()

        batchProgressLabel.value = '正在读取模型特征列…'
        await nextTick()
        const minfo = await apiService.getModelInfo(form.value.modelId)
        if (minfo && minfo.error) {
          throw new Error(minfo.error || '无法读取模型信息')
        }
        const fnames = minfo.feature_names
        const headerLc = new Set(headers.map((h) => String(h).trim().toLowerCase()))
        let useByName = false
        if (Array.isArray(fnames) && fnames.length > 0) {
          const hits = fnames.filter((n) => headerLc.has(String(n).trim().toLowerCase())).length
          useByName = hits / fnames.length >= 0.6
        }

        const featureRows = dataRows.map((row) => {
          if (useByName) {
            const v = featureVectorFromModelColumnNames(row, fnames)
            if (v) return v
          }
          return rowToFeatureVector(row)
        })
        const results = new Array(total)
        const numChunks = Math.ceil(total / PREDICT_BATCH_CHUNK)

        for (let c = 0; c < numChunks; c++) {
          const from = c * PREDICT_BATCH_CHUNK
          const to = Math.min(from + PREDICT_BATCH_CHUNK, total)
          const sliceFeatures = featureRows.slice(from, to)

          batchProgressLabel.value = `正在请求第 ${c + 1} / ${numChunks} 批（${from + 1}–${to} / ${total}）…`
          await nextTick()

          const body = await apiService.predictBatch({
            model_id: form.value.modelId,
            features_rows: sliceFeatures
          })
          const batchResults = body.results || body.data?.results
          if (!batchResults || batchResults.length !== to - from) {
            throw new Error('批量预测返回数据条数与请求不一致')
          }

          for (let i = 0; i < batchResults.length; i++) {
            const row = dataRows[from + i]
            const prediction = batchResults[i]
            results[from + i] = {
              ...row,
              prediction: prediction.prediction,
              confidence: prediction.confidence ?? 0,
              probability: prediction.probability || [0, 0],
              riskScore: (prediction.probability && prediction.probability[1]
                ? prediction.probability[1] * 100
                : 0
              ).toFixed(1)
            }
          }

          const done = to
          batchProgressPercent.value = Math.min(100, Math.round((done / total) * 100))
          await nextTick()
        }

        batchProgressPercent.value = 100
        batchProgressLabel.value = '正在刷新表格…'
        resultPage.value = 1
        riskThreshold.value = 0.5
        predictionResults.value = results
        await nextTick()
        batchProgressLabel.value = ''
        ElMessage.success(`批量预测完成，共 ${results.length} 条`)
      } catch (error) {
        console.error('批量预测失败:', error)
        ElMessage.error(`批量预测失败: ${error.message || error}`)
      } finally {
        predicting.value = false
        batchProgressPercent.value = 0
        batchProgressLabel.value = ''
      }
    }

    const exportResults = () => {
      if (predictionResults.value.length === 0) {
        ElMessage.warning('没有可导出的结果')
        return
      }

      // 构建CSV内容
      const headers = resultColumns.value.map(col => col.label || col.prop)
      const tau = riskThreshold.value
      headers.push(
        'API类别',
        '正类概率P1',
        `档位_P1≥${tau.toFixed(2)}`,
        '风险评分',
        '置信度'
      )

      const rows = predictionResults.value.map(row => {
        const values = resultColumns.value.map(col => {
          const val = row[col.prop]
          if (val === undefined || val === null) return ''
          if (typeof val === 'object') return JSON.stringify(val)
          return String(val)
        })
        const api = row.prediction === 0 || row.prediction === 1 ? String(row.prediction) : ''
        const p1 = (positiveProb(row) * 100).toFixed(2) + '%'
        const d = displayPred(row)
        const tier =
          d === 1 ? '高风险' : d === 0 ? '低风险' : '失败'
        values.push(api, p1, tier, row.riskScore + '%', (row.confidence * 100).toFixed(1) + '%')
        return values.map((v) => escapeCsvField(v)).join(',')
      })

      const csvContent = [
        headers.map((h) => escapeCsvField(h)).join(','),
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
      resultPage.value = 1
      riskThreshold.value = 0.5
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
      batchProgressPercent,
      batchProgressLabel,
      resultPage,
      resultPageSize,
      pagedResults,
      resultIndexMethod,
      onResultPageSizeChange,
      resultStats,
      riskThreshold,
      thresholdMarks,
      displayPred,
      positiveProb,
      suspicionAlert,
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
      resetForm,
      helpActiveNames
    }
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.card-header--split {
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  width: 100%;
}

.results-title {
  font-weight: 600;
}

.results-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.batch-results-card {
  margin-top: 24px;
}

.batch-result-stats {
  margin-bottom: 20px;
  padding: 16px 18px;
  background: linear-gradient(180deg, #fafbfc 0%, #fff 100%);
  border: 1px solid #ebeef5;
  border-radius: var(--hc-radius-md, 8px);
}

.batch-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.batch-stat-card {
  padding: 12px 14px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.batch-stat-card--wide {
  grid-column: 1 / -1;
}

@media (min-width: 720px) {
  .batch-stat-card--wide {
    grid-column: span 2;
  }
}

.batch-stat-card--danger {
  border-color: #fde2e2;
  background: linear-gradient(180deg, #fff5f5 0%, #fff 100%);
}

.batch-stat-card--success {
  border-color: #e1f3d8;
  background: linear-gradient(180deg, #f6ffed 0%, #fff 100%);
}

.batch-stat-card--muted {
  border-color: #e4e7ed;
  background: #f4f4f5;
}

.batch-stat-label {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

.batch-stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.batch-stat-pct {
  font-size: 13px;
  color: #606266;
}

.batch-stat-line {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.batch-outcome-bar-wrap {
  margin-top: 4px;
}

.batch-outcome-bar {
  display: flex;
  height: 10px;
  border-radius: 6px;
  overflow: hidden;
  background: #ebeef5;
}

.batch-outcome-seg--high {
  background: linear-gradient(90deg, #f78989, #f56c6c);
  min-width: 0;
  transition: width 0.35s ease;
}

.batch-outcome-seg--low {
  background: linear-gradient(90deg, #95d475, #67c23a);
  min-width: 0;
  transition: width 0.35s ease;
}

.batch-outcome-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: #606266;
}

.batch-outcome-legend .dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.dot--high {
  background: #f56c6c;
}

.dot--low {
  background: #67c23a;
}

.batch-label-compare {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #dcdfe6;
  font-size: 13px;
  color: #606266;
  line-height: 1.55;
}

.batch-label-compare-title {
  display: block;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.batch-label-compare-body {
  display: block;
}

.batch-suspicion-alert {
  margin-bottom: 16px;
}

.batch-threshold-panel {
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #dcdfe6;
}

.batch-threshold-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.batch-threshold-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.batch-threshold-hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: #909399;
  line-height: 1.55;
}

.batch-raw-api-note {
  margin: 0 0 12px;
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
  padding: 8px 10px;
  background: #fdf6ec;
  border-radius: 6px;
  border: 1px solid #faecd8;
}

.batch-api-pred {
  font-family: ui-monospace, monospace;
  font-weight: 600;
  color: #606266;
}

.card-header .el-icon {
  margin-right: 10px;
  font-size: 24px;
  color: #409eff;
}

.batch-help-collapse {
  margin-bottom: 8px;
  border: none;
  --el-collapse-header-height: 48px;
}

:deep(.batch-help-collapse .el-collapse-item__header) {
  font-weight: 600;
  color: #303133;
  background: var(--hc-fill-elevated, linear-gradient(180deg, #fafbfc 0%, #fff 100%));
  border-radius: var(--hc-radius-md, 8px);
  padding: 0 16px;
  border: 1px solid #ebeef5;
}

:deep(.batch-help-collapse .el-collapse-item__wrap) {
  border-bottom: none;
}

:deep(.batch-help-collapse .el-collapse-item) {
  margin-bottom: 10px;
  border: none;
}

:deep(.batch-help-collapse .el-collapse-item__content) {
  padding: 16px 18px 18px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-top: none;
  border-radius: 0 0 var(--hc-radius-md, 8px) var(--hc-radius-md, 8px);
}

.batch-help-lead {
  margin: 0 0 12px;
  font-size: 14px;
  color: #606266;
  line-height: 1.65;
}

.batch-help-subtitle {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.batch-form-block {
  margin-top: 8px;
}

.batch-upload-zone {
  width: 100%;
  max-width: 640px;
  padding: 16px 18px 18px;
  border: 2px dashed #dcdfe6;
  border-radius: var(--hc-radius-md, 8px);
  background: linear-gradient(180deg, #fafbfc 0%, #ffffff 100%);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.batch-upload-zone:hover {
  border-color: #b3d8ff;
  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.12);
}

.batch-upload-tip {
  margin-top: 8px;
  color: #909399;
  font-size: 13px;
}

:deep(.el-card__header) {
  padding: 18px 22px;
  border-bottom: 1px solid #f0f2f5;
  background: linear-gradient(180deg, #fafbfc 0%, #ffffff 100%);
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

:deep(.batch-result-table) {
  border-radius: var(--hc-radius-md, 8px);
  overflow: hidden;
}

:deep(.batch-result-table .el-table__inner-wrapper::before) {
  display: none;
}

:deep(.batch-result-table th.el-table__cell) {
  background: #f5f7fa !important;
  font-weight: 600;
  color: #606266;
  font-size: 13px;
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

.batch-progress-wrap {
  max-width: 640px;
  margin-top: 8px;
  padding: 16px 18px;
  background: #f5f9ff;
  border: 1px solid #d9ecff;
  border-radius: var(--hc-radius-md, 8px);
}

.batch-progress-text {
  margin: 10px 0 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.batch-result-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>

