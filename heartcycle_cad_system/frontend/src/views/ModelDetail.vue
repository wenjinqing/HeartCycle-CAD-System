<template>
  <div class="model-detail-page hc-page-shell">
    <!-- 顶部导航 -->
    <el-page-header @back="router.back()" style="margin-bottom: 20px">
      <template #content>
        <span style="font-size: 17px; font-weight: bold">模型训练结果详情</span>
      </template>
    </el-page-header>

    <div v-loading="loading" element-loading-text="加载中...">
      <template v-if="model">
        <!-- ① 基本信息 -->
        <el-card class="section-card hc-card-elevated" shadow="never">
          <el-row :gutter="20" align="middle">
            <el-col :span="18">
              <el-space wrap>
                <el-tag type="primary" size="large">{{ getModelTypeName(model.model_type) }}</el-tag>
                <el-tag v-if="metrics.smote_applied" type="success">SMOTE已应用</el-tag>
                <span style="color:#606266; font-size:13px">
                  模型ID：{{ model.model_id }}
                </span>
                <span style="color:#909399; font-size:13px">
                  创建时间：{{ formatDate(model.created_at) }}
                </span>
              </el-space>
            </el-col>
            <el-col :span="6" style="text-align:right">
              <el-button type="danger" size="small" @click="handleDelete">
                <el-icon><Delete /></el-icon> 删除模型
              </el-button>
            </el-col>
          </el-row>
        </el-card>

        <!-- ② 关键指标卡片 -->
        <el-row :gutter="16" class="metric-cards">
          <el-col :span="5" v-for="card in metricCards" :key="card.label">
            <el-card shadow="hover" class="metric-card" :style="`border-top: 4px solid ${card.color}`">
              <div class="mc-label">{{ card.label }}</div>
              <div class="mc-value" :style="`color:${card.color}`">{{ card.value }}</div>
              <div class="mc-std" v-if="card.std != null">± {{ card.std }}</div>
            </el-card>
          </el-col>
        </el-row>

        <!-- ③ ROC曲线 + 混淆矩阵 -->
        <el-row :gutter="20" class="section-row">
          <el-col :span="12">
            <el-card class="section-card hc-card-elevated" shadow="never">
              <template #header><b>ROC 曲线</b></template>
              <ROCCurve
                v-if="auc != null"
                :auc="auc"
                height="340px"
              />
              <el-empty v-else description="AUC 数据不可用" :image-size="80" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="section-card hc-card-elevated" shadow="never">
              <template #header><b>混淆矩阵</b></template>
              <ConfusionMatrix
                v-if="metrics.confusion_matrix"
                :matrix="metrics.confusion_matrix"
                height="340px"
              />
              <el-empty v-else description="混淆矩阵不可用" :image-size="80" />
            </el-card>
          </el-col>
        </el-row>

        <!-- ④ 交叉验证历史（表格模型） / Keras 摘要（多模态） -->
        <el-row v-if="!isMultimodal" class="section-row">
          <el-col :span="24">
            <el-card class="section-card hc-card-elevated" shadow="never">
              <template #header><b>交叉验证各折性能曲线</b></template>
              <TrainingHistory :metrics="metrics" height="340px" />
            </el-card>
          </el-col>
        </el-row>
        <el-row v-else-if="multimodalConfig?.history" class="section-row">
          <el-col :span="24">
            <el-card class="section-card hc-card-elevated" shadow="never">
              <template #header><b>Keras 训练历史（摘要）</b></template>
              <p class="mm-history-line" v-if="multimodalHistorySummary.epochs">
                共训练 <strong>{{ multimodalHistorySummary.epochs }}</strong> 个 epoch。
                <span v-if="multimodalHistorySummary.bestValAuc != null">
                  验证 AUC 最优 <strong>{{ fmt(multimodalHistorySummary.bestValAuc) }}</strong>
                </span>
                <span v-if="multimodalHistorySummary.lastValAuc != null">
                  ；末轮验证 AUC <strong>{{ fmt(multimodalHistorySummary.lastValAuc) }}</strong>
                </span>
              </p>
              <el-empty v-else description="无 history 曲线数据" :image-size="64" />
            </el-card>
          </el-col>
        </el-row>

        <!-- ⑤ 性能雷达图 + 类别分布 -->
        <el-row v-if="!isMultimodal" :gutter="20" class="section-row">
          <el-col :span="12">
            <el-card class="section-card hc-card-elevated" shadow="never">
              <template #header>
                <div style="display:flex; justify-content:space-between; align-items:center">
                  <b>综合性能图</b>
                  <el-radio-group v-model="chartType" size="small">
                    <el-radio-button value="radar">雷达图</el-radio-button>
                    <el-radio-button value="bar">柱状图</el-radio-button>
                  </el-radio-group>
                </div>
              </template>
              <MetricsComparison
                :metrics="avgMetrics"
                :chart-type="chartType"
                height="340px"
              />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="section-card hc-card-elevated" shadow="never">
              <template #header><b>类别分布对比</b></template>
              <ClassDistribution
                v-if="hasDistribution"
                :original-distribution="metrics.original_class_distribution || {}"
                :resampled-distribution="metrics.resampled_class_distribution || metrics.original_class_distribution || {}"
                :smote-applied="metrics.smote_applied || false"
                height="340px"
              />
              <el-empty v-else description="类别分布数据不可用" :image-size="80" />
            </el-card>
          </el-col>
        </el-row>

        <!-- ⑥ 详细指标表格 -->
        <el-row v-if="!isMultimodal" class="section-row">
          <el-col :span="24">
            <el-card class="section-card hc-card-elevated" shadow="never">
              <template #header><b>各折详细指标</b></template>
              <el-table :data="cvTableData" border stripe size="small">
                <el-table-column label="指标" prop="label" width="120" />
                <el-table-column label="均值" width="100">
                  <template #default="{row}">
                    <el-tag :type="getScoreTag(row.mean)">{{ fmt(row.mean) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="标准差" width="90">
                  <template #default="{row}">{{ fmt(row.std) }}</template>
                </el-table-column>
                <el-table-column :label="`Fold 1`" width="85">
                  <template #default="{row}">{{ fmt(row.scores?.[0]) }}</template>
                </el-table-column>
                <el-table-column :label="`Fold 2`" width="85">
                  <template #default="{row}">{{ fmt(row.scores?.[1]) }}</template>
                </el-table-column>
                <el-table-column :label="`Fold 3`" width="85">
                  <template #default="{row}">{{ fmt(row.scores?.[2]) }}</template>
                </el-table-column>
                <el-table-column :label="`Fold 4`" width="85">
                  <template #default="{row}">{{ fmt(row.scores?.[3]) }}</template>
                </el-table-column>
                <el-table-column :label="`Fold 5`" width="85">
                  <template #default="{row}">{{ fmt(row.scores?.[4]) }}</template>
                </el-table-column>
                <el-table-column label="最大值" width="90">
                  <template #default="{row}">
                    {{ row.scores ? fmt(Math.max(...row.scores.filter(v => v != null))) : 'N/A' }}
                  </template>
                </el-table-column>
                <el-table-column label="最小值" width="90">
                  <template #default="{row}">
                    {{ row.scores ? fmt(Math.min(...row.scores.filter(v => v != null))) : 'N/A' }}
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>

        <!-- ⑦ 模型信息 -->
        <el-row class="section-row">
          <el-col :span="24">
            <el-card class="section-card hc-card-elevated" shadow="never">
              <template #header><b>模型训练信息</b></template>
              <el-descriptions :column="3" border size="small">
                <el-descriptions-item label="模型类型">
                  <el-tag>{{ getModelTypeName(model.model_type) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="特征数量">{{ model.feature_count ?? 'N/A' }}</el-descriptions-item>
                <el-descriptions-item label="交叉验证折数">
                  {{ isMultimodal ? (metrics.cv_folds_note || '固定 train/val/test（非 K 折）') : (metrics.cv_folds ?? 'N/A') }}
                </el-descriptions-item>
                <el-descriptions-item label="SMOTE数据平衡">
                  <template v-if="isMultimodal">
                    <el-tag type="info">不适用（Keras 多模态）</el-tag>
                  </template>
                  <el-tag v-else :type="metrics.smote_applied ? 'success' : 'info'">
                    {{ metrics.smote_applied ? '已应用' : '未应用' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="原始样本数">{{ metrics.original_samples ?? 'N/A' }}</el-descriptions-item>
                <el-descriptions-item label="重采样后样本数">
                  {{ isMultimodal ? '不适用' : (metrics.resampled_samples ?? 'N/A') }}
                </el-descriptions-item>
                <el-descriptions-item label="准确率（CV 均值，推荐）">
                  <el-tag :type="getScoreTag(metrics.accuracy?.mean)">{{ fmt(metrics.accuracy?.mean) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="AUC（CV 均值，推荐）">
                  <el-tag :type="getScoreTag(metrics.roc_auc?.mean)">{{ fmt(metrics.roc_auc?.mean) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="F1（CV 均值，推荐）">
                  <el-tag :type="getScoreTag(metrics.f1?.mean)">{{ fmt(metrics.f1?.mean) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="全量训练集回测准确率" :span="3">
                  <span style="color:#909399;font-size:12px">在 SMOTE 后全部训练样本上重拟合再预测，易过拟合、常接近 1，仅作参考。</span>
                  <el-tag :type="getScoreTag(metrics.final_accuracy)" style="margin-left:8px">{{ fmt(metrics.final_accuracy) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="全量训练集回测 AUC" :span="3">
                  <el-tag :type="getScoreTag(metrics.final_roc_auc)">{{ fmt(metrics.final_roc_auc) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="全量训练集回测 F1" :span="3">
                  <el-tag :type="getScoreTag(metrics.final_f1)">{{ fmt(metrics.final_f1) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="创建时间" :span="3">{{ formatDate(model.created_at) }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
        </el-row>
      </template>

      <el-empty v-else-if="!loading" description="模型数据不存在" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { apiService } from '@/services/api'
import ROCCurve from '@/components/charts/ROCCurve.vue'
import ConfusionMatrix from '@/components/charts/ConfusionMatrix.vue'
import TrainingHistory from '@/components/charts/TrainingHistory.vue'
import MetricsComparison from '@/components/charts/MetricsComparison.vue'
import ClassDistribution from '@/components/charts/ClassDistribution.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const model = ref(null)
const chartType = ref('radar')

// 从模型数据中提取 metrics
const metrics = computed(() => {
  // 优先取 model.metrics，其次取 model.metadata?.metrics
  return model.value?.metrics || model.value?.metadata?.metrics || {}
})

const isMultimodal = computed(
  () => model.value?.model_type === 'multimodal_fusion'
)

const multimodalConfig = computed(() => metrics.value?.multimodal || null)

const multimodalHistorySummary = computed(() => {
  const h = multimodalConfig.value?.history
  if (!h || typeof h !== 'object') {
    return { epochs: 0, bestValAuc: null, lastValAuc: null }
  }
  const valAuc = h.val_auc || h.valAuc
  const loss = h.loss
  const epochs = Array.isArray(valAuc)
    ? valAuc.length
    : Array.isArray(loss)
      ? loss.length
      : 0
  let bestValAuc = null
  let lastValAuc = null
  if (Array.isArray(valAuc) && valAuc.length) {
    const nums = valAuc.map((x) => Number(x)).filter((x) => !Number.isNaN(x))
    if (nums.length) {
      bestValAuc = Math.max(...nums)
      lastValAuc = nums[nums.length - 1]
    }
  }
  return { epochs, bestValAuc, lastValAuc }
})

// AUC：与仪表板一致，优先 K 折 CV 均值（final_roc_auc 为全量训练集回测，易虚高）
const auc = computed(() => {
  const m = metrics.value
  return m.roc_auc?.mean ?? m.final_roc_auc ?? null
})

// 是否有类别分布数据
const hasDistribution = computed(() => {
  return !!metrics.value?.original_class_distribution
})

// 各指标均值（用于雷达图/柱状图）
const avgMetrics = computed(() => ({
  accuracy: metrics.value.accuracy?.mean ?? metrics.value.final_accuracy ?? null,
  precision: metrics.value.precision?.mean ?? metrics.value.final_precision ?? null,
  recall: metrics.value.recall?.mean ?? metrics.value.final_recall ?? null,
  f1: metrics.value.f1?.mean ?? metrics.value.final_f1 ?? null,
  roc_auc: metrics.value.roc_auc?.mean ?? metrics.value.final_roc_auc ?? null
}))

// 顶部指标卡
const metricCards = computed(() => [
  {
    label: '准确率',
    value: fmt(avgMetrics.value.accuracy),
    std: metrics.value.accuracy?.std != null ? fmt(metrics.value.accuracy.std) : null,
    color: '#409EFF'
  },
  {
    label: 'ROC AUC',
    value: fmt(auc.value),
    std: metrics.value.roc_auc?.std != null ? fmt(metrics.value.roc_auc.std) : null,
    color: '#9B59B6'
  },
  {
    label: '精确率',
    value: fmt(avgMetrics.value.precision),
    std: metrics.value.precision?.std != null ? fmt(metrics.value.precision.std) : null,
    color: '#67C23A'
  },
  {
    label: '召回率',
    value: fmt(avgMetrics.value.recall),
    std: metrics.value.recall?.std != null ? fmt(metrics.value.recall.std) : null,
    color: '#E6A23C'
  },
  {
    label: 'F1 分数',
    value: fmt(avgMetrics.value.f1),
    std: metrics.value.f1?.std != null ? fmt(metrics.value.f1.std) : null,
    color: '#F56C6C'
  }
])

// 交叉验证表格数据
const cvTableData = computed(() => {
  const m = metrics.value
  return [
    { label: '准确率', mean: m.accuracy?.mean, std: m.accuracy?.std, scores: m.accuracy?.scores },
    { label: '精确率', mean: m.precision?.mean, std: m.precision?.std, scores: m.precision?.scores },
    { label: '召回率', mean: m.recall?.mean, std: m.recall?.std, scores: m.recall?.scores },
    { label: 'F1 分数', mean: m.f1?.mean, std: m.f1?.std, scores: m.f1?.scores },
    { label: 'ROC AUC', mean: m.roc_auc?.mean, std: m.roc_auc?.std, scores: m.roc_auc?.scores }
  ].filter(row => row.mean != null)
})

// 加载模型数据
async function loadModel() {
  loading.value = true
  try {
    const res = await apiService.getModelInfo(route.params.id)
    // ModelInfoResponse 为扁平结构（无 data 包裹）；部分接口仍可能返回 { success, data }
    if (res?.success) {
      model.value = res.data != null ? res.data : res
    } else if (res?.model_id) {
      model.value = res
    } else {
      ElMessage.error('获取模型数据失败')
    }
  } catch (e) {
    ElMessage.error('加载失败：' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(`确定删除模型 "${model.value.model_id}"？`, '确认删除', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消'
    })
    await apiService.deleteModel(model.value.model_id)
    ElMessage.success('模型已删除')
    router.push('/dashboard')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const fmt = (v) => (v == null ? 'N/A' : typeof v === 'number' ? v.toFixed(4) : v)

const getScoreTag = (v) => {
  if (v == null) return 'info'
  if (v >= 0.9) return 'success'
  if (v >= 0.7) return 'warning'
  return 'danger'
}

const formatDate = (d) => {
  if (!d || d === 'unknown') return 'N/A'
  if (typeof d === 'string' && /^\d{8}_\d{6}$/.test(d.trim())) {
    const s = d.trim()
    const y = s.slice(0, 4)
    const mo = s.slice(4, 6)
    const da = s.slice(6, 8)
    const h = s.slice(9, 11)
    const mi = s.slice(11, 13)
    const sec = s.slice(13, 15)
    const iso = `${y}-${mo}-${da}T${h}:${mi}:${sec}`
    const dt = new Date(iso)
    return Number.isNaN(dt.getTime()) ? s : dt.toLocaleString('zh-CN')
  }
  const dt = new Date(d)
  return Number.isNaN(dt.getTime()) ? String(d) : dt.toLocaleString('zh-CN')
}

const getModelTypeName = (t) => ({
  lr: '逻辑回归', rf: '随机森林', xgb: 'XGBoost',
  lgb: 'LightGBM', svm: '支持向量机',
  stacking: 'Stacking集成', voting: 'Voting集成',
  cnn: 'CNN', lstm: 'LSTM', gru: 'GRU', cnn_lstm: 'CNN-LSTM',
  multimodal_fusion: '多模态融合'
}[t] || t)

onMounted(loadModel)
</script>

<style scoped>
.model-detail-page {
  padding-top: 4px;
}

.section-card {
  margin-bottom: 0;
}

.section-row {
  margin-bottom: 20px;
}

.metric-cards {
  margin: 16px 0;
}

.metric-card {
  text-align: center;
  padding: 4px 0;
}

.mc-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}

.mc-value {
  font-size: 28px;
  font-weight: bold;
  line-height: 1.2;
}

.mc-std {
  font-size: 12px;
  color: #C0C4CC;
  margin-top: 4px;
}
</style>
