<template>
  <div class="dashboard hc-page-shell hc-page-shell--wide">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon><DataBoard /></el-icon>
          <span>模型性能监控仪表板</span>
          <div style="margin-left: auto">
            <el-button type="primary" size="small" @click="loadModelList" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-row :gutter="20" style="margin-bottom: 20px">
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-card">
              <div class="stat-icon" style="background: #409eff">
                <el-icon :size="32"><Box /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ modelList.length }}</div>
                <div class="stat-label">模型总数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-card">
              <div class="stat-icon" style="background: #67c23a">
                <el-icon :size="32"><Check /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ averageAccuracy }}%</div>
                <div class="stat-label">平均准确率</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-card">
              <div class="stat-icon" style="background: #e6a23c">
                <el-icon :size="32"><TrendCharts /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ averageAUC }}</div>
                <div class="stat-label">平均AUC（曲线下面积）</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="stat-card">
              <div class="stat-icon" style="background: #f56c6c">
                <el-icon :size="32"><DataAnalysis /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ averageF1 }}</div>
                <div class="stat-label">平均F1（F1分数）</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 模型列表和性能指标 -->
      <el-card class="hc-card-elevated" shadow="never" style="margin-top: 20px">
        <template #header>
          <span>模型性能详情</span>
        </template>
        <el-table
          :data="modelList"
          class="dashboard-model-table"
          style="width: 100%"
          v-loading="loading"
          stripe
          :row-key="getRowKey"
        >
          <el-table-column type="expand" width="50">
            <template #default="{ row }">
              <div class="model-detail-expand" v-if="row.metrics">
                <el-row :gutter="20">
                  <!-- 性能指标卡片 -->
                  <el-col :span="24">
                    <div class="expand-section">
                      <h4 class="expand-title">性能指标详情</h4>
                      <p class="expand-metric-hint">主数字为 <strong>K 折交叉验证均值</strong>（泛化估计）；全量训练集回测见下方「模型训练信息」。</p>
                      <el-row :gutter="15">
                        <el-col :span="6">
                          <div class="expand-metric-card">
                            <div class="expand-metric-label">准确率（CV 均值）</div>
                            <div class="expand-metric-value">
                              {{ formatMetric(primaryMetric(row.metrics, 'accuracy', 'final_accuracy')) }}
                            </div>
                            <div class="expand-metric-cv" v-if="row.metrics?.accuracy && row.metrics.accuracy.std != null">
                              标准差: ± {{ formatScore(row.metrics.accuracy.std) }}
                            </div>
                          </div>
                        </el-col>
                        <el-col :span="6">
                          <div class="expand-metric-card">
                            <div class="expand-metric-label">精确率（CV 均值）</div>
                            <div class="expand-metric-value">
                              {{ formatMetric(primaryMetric(row.metrics, 'precision', 'final_precision')) }}
                            </div>
                            <div class="expand-metric-cv" v-if="row.metrics?.precision && row.metrics.precision.std != null">
                              标准差: ± {{ formatScore(row.metrics.precision.std) }}
                            </div>
                          </div>
                        </el-col>
                        <el-col :span="6">
                          <div class="expand-metric-card">
                            <div class="expand-metric-label">召回率（CV 均值）</div>
                            <div class="expand-metric-value">
                              {{ formatMetric(primaryMetric(row.metrics, 'recall', 'final_recall')) }}
                            </div>
                            <div class="expand-metric-cv" v-if="row.metrics?.recall && row.metrics.recall.std != null">
                              标准差: ± {{ formatScore(row.metrics.recall.std) }}
                            </div>
                          </div>
                        </el-col>
                        <el-col :span="6">
                          <div class="expand-metric-card">
                            <div class="expand-metric-label">F1（CV 均值）</div>
                            <div class="expand-metric-value">
                              {{ formatMetric(primaryMetric(row.metrics, 'f1', 'final_f1')) }}
                            </div>
                            <div class="expand-metric-cv" v-if="row.metrics?.f1 && row.metrics.f1.std != null">
                              标准差: ± {{ formatScore(row.metrics.f1.std) }}
                            </div>
                          </div>
                        </el-col>
                      </el-row>
                      <el-row :gutter="15" style="margin-top: 15px">
                        <el-col :span="6">
                          <div class="expand-metric-card">
                            <div class="expand-metric-label">ROC AUC（CV 均值）</div>
                            <div class="expand-metric-value">
                              {{ formatMetric(primaryMetric(row.metrics, 'roc_auc', 'final_roc_auc')) }}
                            </div>
                            <div class="expand-metric-cv" v-if="row.metrics?.roc_auc && row.metrics.roc_auc.mean !== null && row.metrics.roc_auc.std != null">
                              标准差: ± {{ formatScore(row.metrics.roc_auc.std) }}
                            </div>
                          </div>
                        </el-col>
                      </el-row>
                    </div>
                  </el-col>
                </el-row>

                <!-- 交叉验证分数详情 -->
                <el-row :gutter="20" style="margin-top: 20px">
                  <el-col :span="24">
                    <div class="expand-section">
                      <h4 class="expand-title">交叉验证分数详情</h4>
                      <el-table :data="getCvScoresForModel(row)" border size="small" style="margin-top: 10px">
                        <el-table-column prop="metric" label="指标" width="120" />
                        <el-table-column prop="mean" label="平均值" width="120" align="center" />
                        <el-table-column prop="std" label="标准差" width="120" align="center" />
                        <el-table-column prop="scores" label="各折分数" min-width="300">
                          <template #default="{ row: cvRow }">
                            <el-tag
                              v-for="(score, index) in cvRow.scores"
                              :key="index"
                              size="small"
                              style="margin-right: 5px; margin-bottom: 5px"
                            >
                              Fold {{ index + 1 }}: {{ formatScore(score) }}
                            </el-tag>
                          </template>
                        </el-table-column>
                      </el-table>
                    </div>
                  </el-col>
                </el-row>

                <!-- 混淆矩阵 -->
                <el-row :gutter="20" style="margin-top: 20px" v-if="row.metrics?.confusion_matrix">
                  <el-col :span="24">
                    <div class="expand-section">
                      <h4 class="expand-title">混淆矩阵</h4>
                      <div class="confusion-matrix-small">
                        <table class="confusion-table-small">
                          <thead>
                            <tr>
                              <th></th>
                              <th>预测: 低风险</th>
                              <th>预测: 高风险</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr>
                              <th>实际: 低风险</th>
                              <td class="correct">{{ row.metrics.confusion_matrix[0]?.[0] || 0 }}</td>
                              <td class="error">{{ row.metrics.confusion_matrix[0]?.[1] || 0 }}</td>
                            </tr>
                            <tr>
                              <th>实际: 高风险</th>
                              <td class="error">{{ row.metrics.confusion_matrix[1]?.[0] || 0 }}</td>
                              <td class="correct">{{ row.metrics.confusion_matrix[1]?.[1] || 0 }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </el-col>
                </el-row>

                <!-- 模型信息 -->
                <el-row :gutter="20" style="margin-top: 20px">
                  <el-col :span="24">
                    <div class="expand-section">
                      <h4 class="expand-title">模型信息</h4>
                      <el-descriptions :column="3" border size="small">
                        <el-descriptions-item label="特征数量">
                          {{ row.feature_count || 'N/A' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="交叉验证折数">
                          {{ row.metrics?.cv_folds || 'N/A' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="创建时间">
                          {{ formatDate(row.created_at) }}
                        </el-descriptions-item>
                      </el-descriptions>
                    </div>
                  </el-col>
                </el-row>
              </div>
              <el-empty v-else description="该模型暂无性能指标数据" :image-size="80" />
            </template>
          </el-table-column>
          <el-table-column prop="model_id" label="模型ID" width="200" show-overflow-tooltip />
          <el-table-column prop="model_type" label="模型类型" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getModelTypeTag(row.model_type)">
                {{ getModelTypeName(row.model_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="准确率(CV)" width="120" align="center" sortable>
            <template #default="{ row }">
              {{ formatMetric(primaryMetric(row.metrics, 'accuracy', 'final_accuracy')) }}
            </template>
          </el-table-column>
          <el-table-column label="精确率(CV)" width="120" align="center" sortable>
            <template #default="{ row }">
              {{ formatMetric(primaryMetric(row.metrics, 'precision', 'final_precision')) }}
            </template>
          </el-table-column>
          <el-table-column label="召回率(CV)" width="120" align="center" sortable>
            <template #default="{ row }">
              {{ formatMetric(primaryMetric(row.metrics, 'recall', 'final_recall')) }}
            </template>
          </el-table-column>
          <el-table-column label="F1(CV)" width="120" align="center" sortable>
            <template #default="{ row }">
              {{ formatMetric(primaryMetric(row.metrics, 'f1', 'final_f1')) }}
            </template>
          </el-table-column>
          <el-table-column label="ROC AUC(CV)" width="200" align="center" sortable>
            <template #default="{ row }">
              {{ formatMetric(primaryMetric(row.metrics, 'roc_auc', 'final_roc_auc')) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                size="small"
                @click="viewModelDetail(row)"
              >
                查看详情
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click="handleDeleteModel(row)"
                style="margin-left: 8px"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 性能指标对比图表 -->
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <span>准确率对比</span>
            </template>
            <div ref="accuracyChartRef" style="width: 100%; height: 300px;"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <span>AUC（曲线下面积）对比</span>
            </template>
            <div ref="aucChartRef" style="width: 100%; height: 300px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="24">
          <el-card shadow="hover">
            <template #header>
              <span>综合性能雷达图</span>
            </template>
            <div ref="radarChartRef" style="width: 100%; height: 400px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 模型详情对话框 -->
      <el-dialog
        v-model="detailVisible"
        title="模型性能详情"
        width="1000px"
        :before-close="handleDetailClose"
      >
        <div v-if="currentModel">
          <!-- 基本信息 -->
          <el-card class="hc-card-elevated" shadow="never" style="margin-bottom: 20px">
            <template #header>
              <span style="font-weight: 600">基本信息</span>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="模型ID">
                <el-tag type="info">{{ currentModel.model_id }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="模型类型">
                <el-tag :type="getModelTypeTag(currentModel.model_type)">
                  {{ getModelTypeName(currentModel.model_type) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="特征数量">
                {{ currentModel.feature_count || 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="交叉验证折数">
                {{ currentModel.metrics?.cv_folds || 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="创建时间" :span="2">
                {{ formatDate(currentModel.created_at) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 性能指标概览 -->
          <el-card v-if="currentModel.metrics" class="hc-card-elevated" shadow="never" style="margin-bottom: 20px">
            <template #header>
              <span style="font-weight: 600">性能指标概览</span>
            </template>
            <el-row :gutter="20">
              <el-col :span="6">
                <div class="metric-card">
                  <div class="metric-label">准确率（CV 均值）</div>
                  <div class="metric-value">
                    {{ formatMetric(primaryMetric(currentModel.metrics, 'accuracy', 'final_accuracy')) }}
                  </div>
                  <div class="metric-cv" v-if="currentModel.metrics?.accuracy && currentModel.metrics.accuracy.std != null">
                    标准差: ± {{ formatScore(currentModel.metrics.accuracy.std) }}
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card">
                  <div class="metric-label">精确率（CV 均值）</div>
                  <div class="metric-value">
                    {{ formatMetric(primaryMetric(currentModel.metrics, 'precision', 'final_precision')) }}
                  </div>
                  <div class="metric-cv" v-if="currentModel.metrics?.precision && currentModel.metrics.precision.std != null">
                    标准差: ± {{ formatScore(currentModel.metrics.precision.std) }}
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card">
                  <div class="metric-label">召回率（CV 均值）</div>
                  <div class="metric-value">
                    {{ formatMetric(primaryMetric(currentModel.metrics, 'recall', 'final_recall')) }}
                  </div>
                  <div class="metric-cv" v-if="currentModel.metrics?.recall && currentModel.metrics.recall.std != null">
                    标准差: ± {{ formatScore(currentModel.metrics.recall.std) }}
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card">
                  <div class="metric-label">F1（CV 均值）</div>
                  <div class="metric-value">
                    {{ formatMetric(primaryMetric(currentModel.metrics, 'f1', 'final_f1')) }}
                  </div>
                  <div class="metric-cv" v-if="currentModel.metrics?.f1 && currentModel.metrics.f1.std != null">
                    标准差: ± {{ formatScore(currentModel.metrics.f1.std) }}
                  </div>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 20px">
              <el-col :span="12">
                <div class="metric-card">
                  <div class="metric-label">ROC AUC（CV 均值）</div>
                  <div class="metric-value">
                    {{ formatMetric(primaryMetric(currentModel.metrics, 'roc_auc', 'final_roc_auc')) }}
                  </div>
                  <div class="metric-cv" v-if="currentModel.metrics?.roc_auc && currentModel.metrics.roc_auc.std != null">
                    标准差: ± {{ formatScore(currentModel.metrics.roc_auc.std) }}
                  </div>
                </div>
              </el-col>
            </el-row>
          </el-card>

          <!-- 交叉验证分数可视化 -->
          <el-card v-if="currentModel.metrics && cvScoresData.length > 0" class="hc-card-elevated" shadow="never" style="margin-bottom: 20px">
            <template #header>
              <span style="font-weight: 600">交叉验证分数分布</span>
            </template>
            <div ref="detailCvChartRef" style="width: 100%; height: 350px;"></div>
          </el-card>

          <!-- 交叉验证分数详情表格 -->
          <el-card v-if="cvScoresData.length > 0" class="hc-card-elevated" shadow="never" style="margin-bottom: 20px">
            <template #header>
              <span style="font-weight: 600">交叉验证分数详情</span>
            </template>
            <el-table :data="cvScoresData" stripe>
              <el-table-column prop="metric" label="指标" width="120" />
              <el-table-column prop="mean" label="平均值" width="120" align="center" />
              <el-table-column prop="std" label="标准差" width="120" align="center" />
              <el-table-column prop="scores" label="各折分数" min-width="300">
                <template #default="{ row }">
                  <el-tag
                    v-for="(score, index) in row.scores"
                    :key="index"
                    size="small"
                    style="margin-right: 5px; margin-bottom: 5px"
                  >
                    Fold {{ index + 1 }}: {{ formatScore(score) }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <!-- 混淆矩阵 -->
          <el-card v-if="currentModel.metrics?.confusion_matrix" class="hc-card-elevated" shadow="never">
            <template #header>
              <span style="font-weight: 600">混淆矩阵</span>
            </template>
            <div class="confusion-matrix">
              <table class="confusion-table">
                <thead>
                  <tr>
                    <th></th>
                    <th>预测: 低风险</th>
                    <th>预测: 高风险</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th>实际: 低风险</th>
                    <td>{{ currentModel.metrics.confusion_matrix[0]?.[0] || 0 }}</td>
                    <td>{{ currentModel.metrics.confusion_matrix[0]?.[1] || 0 }}</td>
                  </tr>
                  <tr>
                    <th>实际: 高风险</th>
                    <td>{{ currentModel.metrics.confusion_matrix[1]?.[0] || 0 }}</td>
                    <td>{{ currentModel.metrics.confusion_matrix[1]?.[1] || 0 }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </el-card>

          <el-empty v-if="!currentModel.metrics" description="该模型暂无性能指标数据" />
        </div>
      </el-dialog>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataBoard,
  Refresh,
  Box,
  Check,
  TrendCharts,
  DataAnalysis
} from '@element-plus/icons-vue'
import { apiService } from '../services/api'
import { primaryMetric } from '../utils/metricsDisplay'
import * as echarts from 'echarts'

export default {
  name: 'Dashboard',
  components: {
    DataBoard,
    Refresh,
    Box,
    Check,
    TrendCharts,
    DataAnalysis
  },
  setup() {
    const router = useRouter()
    const loading = ref(false)
    const modelList = ref([])
    const detailVisible = ref(false)
    const currentModel = ref(null)
    
    const accuracyChartRef = ref(null)
    const aucChartRef = ref(null)
    const radarChartRef = ref(null)
    const detailCvChartRef = ref(null)
    let accuracyChart = null
    let aucChart = null
    let radarChart = null
    let detailCvChart = null

    const averageAccuracy = computed(() => {
      const modelsWithMetrics = modelList.value.filter(m => m.metrics)
      if (modelsWithMetrics.length === 0) return '0.00'
      const sum = modelsWithMetrics.reduce((acc, model) => {
        const accValue = primaryMetric(model.metrics, 'accuracy', 'final_accuracy') || 0
        return acc + (typeof accValue === 'number' ? accValue : 0)
      }, 0)
      return ((sum / modelsWithMetrics.length) * 100).toFixed(2)
    })

    const averageAUC = computed(() => {
      if (modelList.value.length === 0) return '0.0000'
      const validModels = modelList.value.filter(model => {
        const auc = primaryMetric(model.metrics, 'roc_auc', 'final_roc_auc')
        return auc !== null && auc !== undefined && !isNaN(auc)
      })
      if (validModels.length === 0) return 'N/A'
      const sum = validModels.reduce((acc, model) => {
        const aucValue = primaryMetric(model.metrics, 'roc_auc', 'final_roc_auc') || 0
        return acc + (typeof aucValue === 'number' ? aucValue : 0)
      }, 0)
      return (sum / validModels.length).toFixed(4)
    })

    const averageF1 = computed(() => {
      const modelsWithMetrics = modelList.value.filter(m => m.metrics)
      if (modelsWithMetrics.length === 0) return '0.0000'
      const sum = modelsWithMetrics.reduce((acc, model) => {
        const f1Value = primaryMetric(model.metrics, 'f1', 'final_f1') || 0
        return acc + (typeof f1Value === 'number' ? f1Value : 0)
      }, 0)
      return (sum / modelsWithMetrics.length).toFixed(4)
    })

    const getModelTypeName = (type) => {
      const typeMap = {
        'lr': 'LR（逻辑回归）',
        'svm': 'SVM（支持向量机）',
        'rf': 'RF（随机森林）'
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

    const formatMetric = (value) => {
      if (value === null || value === undefined || isNaN(value)) return 'N/A'
      return (typeof value === 'number' ? value : parseFloat(value)).toFixed(4)
    }

    const formatScore = (value) => {
      if (value === null || value === undefined || isNaN(value)) return 'N/A'
      return (typeof value === 'number' ? value : parseFloat(value)).toFixed(3)
    }

    const formatDate = (dateStr) => {
      if (!dateStr || dateStr === 'unknown' || dateStr === 'N/A') return 'N/A'
      try {
        // 处理 ISO 格式字符串（如 "2025-12-31T14:30:00"）
        let date
        if (typeof dateStr === 'string') {
          // 尝试解析 ISO 格式
          date = new Date(dateStr)
          // 检查日期是否有效
          if (isNaN(date.getTime())) {
            // 如果不是有效的日期，尝试其他格式
            // 可能是时间戳格式（如 "20251231_143000"）
            if (dateStr.match(/^\d{8}_\d{6}$/)) {
              // 格式: YYYYMMDD_HHMMSS
              const year = dateStr.substring(0, 4)
              const month = dateStr.substring(4, 6)
              const day = dateStr.substring(6, 8)
              const hour = dateStr.substring(9, 11)
              const minute = dateStr.substring(11, 13)
              const second = dateStr.substring(13, 15)
              date = new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}`)
            } else {
              return dateStr // 无法解析，返回原字符串
            }
          }
        } else {
          date = new Date(dateStr)
        }
        
        // 再次检查日期是否有效
        if (isNaN(date.getTime())) {
          return dateStr
        }
        
        return date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
      } catch (e) {
        return dateStr
      }
    }

    const loadModelList = async () => {
      try {
        loading.value = true
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
        
        // 获取每个模型的详细信息
        const modelDetails = await Promise.all(
          models.map(async (model) => {
            try {
              const detailResponse = await apiService.getModelInfo(model.model_id)
              return detailResponse.data || detailResponse
            } catch (error) {
              console.warn(`获取模型 ${model.model_id} 详情失败:`, error)
              return model
            }
          })
        )
        
        // 显示所有模型，包括没有metrics的模型
        modelList.value = modelDetails.filter(m => m)
        
        // 初始化图表
        nextTick(() => {
          initCharts()
        })
      } catch (error) {
        console.error('加载模型列表失败:', error)
        ElMessage.error(`加载模型列表失败: ${error.message}`)
      } finally {
        loading.value = false
      }
    }

    const initCharts = () => {
      initAccuracyChart()
      initAucChart()
      initRadarChart()
    }

    const initAccuracyChart = () => {
      if (!accuracyChartRef.value || modelList.value.length === 0) return

      if (accuracyChart) {
        accuracyChart.dispose()
      }

      accuracyChart = echarts.init(accuracyChartRef.value)

      // 只显示有metrics的模型
      const modelsWithMetrics = modelList.value.filter(m => m.metrics)
      if (modelsWithMetrics.length === 0) {
        accuracyChart.setOption({
          title: {
            text: '暂无准确率数据',
            left: 'center',
            top: 'middle'
          }
        })
        return
      }

      const modelIds = modelsWithMetrics.map(m => m.model_id.substring(0, 15) + '...')
      const accuracies = modelsWithMetrics.map(m => {
        const acc = primaryMetric(m.metrics, 'accuracy', 'final_accuracy') || 0
        return (typeof acc === 'number' ? acc : parseFloat(acc)) * 100
      })

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const param = params[0]
            return `${param.seriesName}<br/>${param.name}: ${param.value.toFixed(2)}%`
          },
          backgroundColor: 'rgba(50, 50, 50, 0.9)',
          borderColor: '#409eff',
          borderWidth: 1,
          textStyle: {
            color: '#fff'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: modelIds,
          axisLabel: {
            rotate: 45,
            fontSize: 10,
            interval: 0
          },
          axisLine: {
            lineStyle: {
              color: '#dcdfe6'
            }
          }
        },
        yAxis: {
          type: 'value',
          name: '准确率 (%)',
          min: 0,
          max: 100,
          axisLine: {
            lineStyle: {
              color: '#dcdfe6'
            }
          },
          splitLine: {
            lineStyle: {
              color: '#f0f2f5'
            }
          }
        },
        series: [{
          name: '准确率',
          type: 'bar',
          data: accuracies,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#83bff6' },
              { offset: 0.5, color: '#188df0' },
              { offset: 1, color: '#188df0' }
            ]),
            borderRadius: [8, 8, 0, 0]
          },
          label: {
            show: true,
            position: 'top',
            formatter: '{c}%',
            fontSize: 11,
            fontWeight: 'bold'
          },
          emphasis: {
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#409eff' },
                { offset: 1, color: '#0066cc' }
              ])
            }
          },
          animationDelay: (idx) => idx * 50
        }],
        animationEasing: 'elasticOut',
        animationDelayUpdate: (idx) => idx * 5
      }

      accuracyChart.setOption(option)
      window.addEventListener('resize', () => {
        if (accuracyChart) accuracyChart.resize()
      })
    }

    const initAucChart = () => {
      if (!aucChartRef.value || modelList.value.length === 0) return

      if (aucChart) {
        aucChart.dispose()
      }

      aucChart = echarts.init(aucChartRef.value)

      // 只显示有AUC数据的模型
      const modelsWithAuc = modelList.value.filter(m => {
        const auc = primaryMetric(m.metrics, 'roc_auc', 'final_roc_auc')
        return auc !== null && auc !== undefined && !isNaN(auc)
      })

      if (modelsWithAuc.length === 0) {
        aucChart.setOption({
          title: {
            text: '暂无AUC数据',
            left: 'center',
            top: 'middle'
          }
        })
        return
      }

      const modelIds = modelsWithAuc.map(m => m.model_id.substring(0, 15) + '...')
      const aucs = modelsWithAuc.map(m => {
        const auc = primaryMetric(m.metrics, 'roc_auc', 'final_roc_auc')
        return parseFloat(auc)
      })

      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const param = params[0]
            return `${param.seriesName}<br/>${param.name}: ${param.value.toFixed(4)}`
          },
          backgroundColor: 'rgba(50, 50, 50, 0.9)',
          borderColor: '#67c23a',
          borderWidth: 1,
          textStyle: {
            color: '#fff'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: modelIds,
          axisLabel: {
            rotate: 45,
            fontSize: 10,
            interval: 0
          },
          axisLine: {
            lineStyle: {
              color: '#dcdfe6'
            }
          }
        },
        yAxis: {
          type: 'value',
          name: 'AUC（曲线下面积）',
          min: 0,
          max: 1,
          axisLine: {
            lineStyle: {
              color: '#dcdfe6'
            }
          },
          splitLine: {
            lineStyle: {
              color: '#f0f2f5'
            }
          }
        },
        series: [{
          name: 'AUC（曲线下面积）',
          type: 'line',
          smooth: true,
          data: aucs,
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: {
            color: '#67c23a',
            borderWidth: 2,
            borderColor: '#fff'
          },
          lineStyle: {
            width: 3,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#67c23a' },
              { offset: 1, color: '#85ce61' }
            ])
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(103, 194, 58, 0.4)' },
              { offset: 1, color: 'rgba(103, 194, 58, 0.05)' }
            ])
          },
          label: {
            show: true,
            position: 'top',
            formatter: '{c}',
            fontSize: 10,
            fontWeight: 'bold'
          },
          emphasis: {
            itemStyle: {
              color: '#67c23a',
              borderWidth: 3,
              shadowBlur: 10,
              shadowColor: 'rgba(103, 194, 58, 0.5)'
            },
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 'bold'
            }
          },
          animationDelay: (idx) => idx * 50
        }],
        animationEasing: 'cubicOut',
        animationDelayUpdate: (idx) => idx * 5
      }

      aucChart.setOption(option)
      window.addEventListener('resize', () => {
        if (aucChart) aucChart.resize()
      })
    }

    const initRadarChart = () => {
      if (!radarChartRef.value || modelList.value.length === 0) return

      if (radarChart) {
        radarChart.dispose()
      }

      radarChart = echarts.init(radarChartRef.value)

      // 选择前5个有metrics的模型进行对比
      const modelsWithMetrics = modelList.value.filter(m => m.metrics)
      if (modelsWithMetrics.length === 0) {
        radarChart.setOption({
          title: {
            text: '暂无性能数据',
            left: 'center',
            top: 'middle'
          }
        })
        return
      }
      const topModels = modelsWithMetrics.slice(0, 5)

      const indicators = [
        { name: '准确率', max: 1 },
        { name: '精确率', max: 1 },
        { name: '召回率', max: 1 },
        { name: 'F1分数', max: 1 },
        { name: 'ROC AUC', max: 1 }
      ]

      const seriesData = topModels.map((model) => {
        const metrics = model.metrics || {}
        return {
          value: [
            primaryMetric(metrics, 'accuracy', 'final_accuracy') || 0,
            primaryMetric(metrics, 'precision', 'final_precision') || 0,
            primaryMetric(metrics, 'recall', 'final_recall') || 0,
            primaryMetric(metrics, 'f1', 'final_f1') || 0,
            primaryMetric(metrics, 'roc_auc', 'final_roc_auc') || 0
          ],
          name: model.model_id.substring(0, 15) + '...'
        }
      })

      const option = {
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(50, 50, 50, 0.9)',
          borderColor: '#409eff',
          borderWidth: 1,
          textStyle: {
            color: '#fff'
          },
          formatter: (params) => {
            const data = params.data
            let result = `<strong>${data.name}</strong><br/>`
            indicators.forEach((indicator, index) => {
              result += `${indicator.name}: ${(data.value[index] * 100).toFixed(2)}%<br/>`
            })
            return result
          }
        },
        legend: {
          data: seriesData.map(s => s.name),
          bottom: 10,
          textStyle: {
            fontSize: 12
          }
        },
        radar: {
          indicator: indicators,
          center: ['50%', '50%'],
          radius: '65%',
          shape: 'polygon',
          splitNumber: 5,
          name: {
            textStyle: {
              color: '#606266',
              fontSize: 13,
              fontWeight: 'bold'
            }
          },
          splitLine: {
            lineStyle: {
              color: '#dcdfe6',
              width: 1
            }
          },
          splitArea: {
            show: true,
            areaStyle: {
              color: ['rgba(64, 158, 255, 0.05)', 'rgba(64, 158, 255, 0.1)']
            }
          },
          axisLine: {
            lineStyle: {
              color: '#dcdfe6',
              width: 2
            }
          }
        },
        series: [{
          name: '模型性能对比',
          type: 'radar',
          data: seriesData.map((item, index) => ({
            ...item,
            areaStyle: {
              color: `rgba(${[64, 103, 230, 245, 144][index % 5]}, ${[158, 194, 162, 108, 238][index % 5]}, ${[255, 58, 35, 108, 144][index % 5]}, 0.2)`
            },
            lineStyle: {
              width: 2,
              color: `rgb(${[64, 103, 230, 245, 144][index % 5]}, ${[158, 194, 230, 108, 238][index % 5]}, ${[255, 58, 35, 108, 144][index % 5]})`
            },
            itemStyle: {
              color: `rgb(${[64, 103, 230, 245, 144][index % 5]}, ${[158, 194, 230, 108, 238][index % 5]}, ${[255, 58, 35, 108, 144][index % 5]})`,
              borderWidth: 2,
              borderColor: '#fff'
            },
            emphasis: {
              lineStyle: {
                width: 3
              },
              itemStyle: {
                borderWidth: 3,
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.3)'
              }
            }
          })),
          animationDelay: (idx) => idx * 100
        }],
        animationEasing: 'elasticOut',
        animationDuration: 1000
      }

      radarChart.setOption(option)
      window.addEventListener('resize', () => {
        if (radarChart) radarChart.resize()
      })
    }

    const getCvScoresForModel = (model) => {
      if (!model || !model.metrics) return []
      
      const metrics = model.metrics
      const data = []
      
      // 准确率
      if (metrics.accuracy && (metrics.accuracy.mean !== null && metrics.accuracy.mean !== undefined)) {
        data.push({
          metric: '准确率',
          mean: formatScore(metrics.accuracy.mean),
          std: formatScore(metrics.accuracy.std),
          scores: metrics.accuracy.scores || []
        })
      } else {
        data.push({
          metric: '准确率',
          mean: 'N/A',
          std: 'N/A',
          scores: []
        })
      }
      
      // 精确率
      if (metrics.precision && (metrics.precision.mean !== null && metrics.precision.mean !== undefined)) {
        data.push({
          metric: '精确率',
          mean: formatScore(metrics.precision.mean),
          std: formatScore(metrics.precision.std),
          scores: metrics.precision.scores || []
        })
      } else {
        data.push({
          metric: '精确率',
          mean: 'N/A',
          std: 'N/A',
          scores: []
        })
      }
      
      // 召回率
      if (metrics.recall && (metrics.recall.mean !== null && metrics.recall.mean !== undefined)) {
        data.push({
          metric: '召回率',
          mean: formatScore(metrics.recall.mean),
          std: formatScore(metrics.recall.std),
          scores: metrics.recall.scores || []
        })
      } else {
        data.push({
          metric: '召回率',
          mean: 'N/A',
          std: 'N/A',
          scores: []
        })
      }
      
      // F1分数
      if (metrics.f1 && (metrics.f1.mean !== null && metrics.f1.mean !== undefined)) {
        data.push({
          metric: 'F1分数',
          mean: formatScore(metrics.f1.mean),
          std: formatScore(metrics.f1.std),
          scores: metrics.f1.scores || []
        })
      } else {
        data.push({
          metric: 'F1分数',
          mean: 'N/A',
          std: 'N/A',
          scores: []
        })
      }
      
      // ROC AUC
      if (metrics.roc_auc && (metrics.roc_auc.mean !== null && metrics.roc_auc.mean !== undefined)) {
        data.push({
          metric: 'ROC AUC',
          mean: formatScore(metrics.roc_auc.mean),
          std: formatScore(metrics.roc_auc.std),
          scores: metrics.roc_auc.scores || []
        })
      } else {
        data.push({
          metric: 'ROC AUC',
          mean: 'N/A',
          std: 'N/A',
          scores: []
        })
      }
      
      return data
    }

    const cvScoresData = computed(() => {
      if (!currentModel.value || !currentModel.value.metrics) return []
      return getCvScoresForModel(currentModel.value)
    })

    const getRowKey = (row) => {
      return row.model_id
    }

    const viewModelDetail = (model) => {
      // Navigate to the dedicated model detail page
      router.push(`/models/${model.model_id}`)
    }

    const handleDetailClose = () => {
      detailVisible.value = false
      // 销毁详情图表
      if (detailCvChart) {
        detailCvChart.dispose()
        detailCvChart = null
      }
    }

    const _initDetailCvChart = () => {
      if (!detailCvChartRef.value || !currentModel.value || !currentModel.value.metrics) return

      if (detailCvChart) {
        detailCvChart.dispose()
      }

      detailCvChart = echarts.init(detailCvChartRef.value)

      const metrics = currentModel.value.metrics
      const categories = []
      const seriesData = []

      // 准备数据
      if (metrics.accuracy && metrics.accuracy.scores) {
        categories.push('准确率')
        seriesData.push({
          name: '准确率',
          type: 'boxplot',
          data: [metrics.accuracy.scores],
          itemStyle: { color: '#409EFF' }
        })
      }
      if (metrics.precision && metrics.precision.scores) {
        categories.push('精确率')
        seriesData.push({
          name: '精确率',
          type: 'boxplot',
          data: [metrics.precision.scores],
          itemStyle: { color: '#67C23A' }
        })
      }
      if (metrics.recall && metrics.recall.scores) {
        categories.push('召回率')
        seriesData.push({
          name: '召回率',
          type: 'boxplot',
          data: [metrics.recall.scores],
          itemStyle: { color: '#E6A23C' }
        })
      }
      if (metrics.f1 && metrics.f1.scores) {
        categories.push('F1分数')
        seriesData.push({
          name: 'F1分数',
          type: 'boxplot',
          data: [metrics.f1.scores],
          itemStyle: { color: '#F56C6C' }
        })
      }
      if (metrics.roc_auc && metrics.roc_auc.scores && metrics.roc_auc.scores.filter(s => s !== null).length > 0) {
        categories.push('ROC AUC')
        seriesData.push({
          name: 'ROC AUC',
          type: 'boxplot',
          data: [metrics.roc_auc.scores.filter(s => s !== null)],
          itemStyle: { color: '#909399' }
        })
      }

      if (seriesData.length === 0) {
        detailCvChart.setOption({
          title: {
            text: '暂无交叉验证数据',
            left: 'center',
            top: 'middle'
          }
        })
        return
      }

      // 获取最大折数
      const maxFolds = Math.max(...categories.map(cat => {
        const metricKey = cat === '准确率' ? 'accuracy' : 
                         cat === '精确率' ? 'precision' :
                         cat === '召回率' ? 'recall' :
                         cat === 'F1分数' ? 'f1' : 'roc_auc'
        const scores = metrics[metricKey]?.scores || []
        return scores.filter(s => s !== null && s !== undefined).length
      }), 1)
      
      const foldLabels = Array.from({ length: maxFolds }, (_, i) => `Fold ${i + 1}`)

      // 使用柱状图显示各折分数
      const option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow',
            shadowStyle: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          },
          backgroundColor: 'rgba(50, 50, 50, 0.9)',
          borderColor: '#409eff',
          borderWidth: 1,
          textStyle: {
            color: '#fff'
          },
          formatter: (params) => {
            let result = `<strong>${params[0].name}</strong><br/>`
            params.forEach(param => {
              result += `${param.marker} ${param.seriesName}: ${formatScore(param.value)}<br/>`
            })
            return result
          }
        },
        legend: {
          data: categories,
          bottom: 10,
          textStyle: {
            fontSize: 12
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: foldLabels,
          boundaryGap: true,
          axisLine: {
            lineStyle: {
              color: '#dcdfe6'
            }
          },
          axisLabel: {
            fontSize: 11
          }
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: 1,
          name: '分数',
          axisLine: {
            lineStyle: {
              color: '#dcdfe6'
            }
          },
          splitLine: {
            lineStyle: {
              color: '#f0f2f5'
            }
          }
        },
        series: categories.map((cat, index) => {
          const metricKey = cat === '准确率' ? 'accuracy' :
                           cat === '精确率' ? 'precision' :
                           cat === '召回率' ? 'recall' :
                           cat === 'F1分数' ? 'f1' : 'roc_auc'
          const scores = metrics[metricKey]?.scores || []
          const validScores = scores.filter(s => s !== null && s !== undefined)

          const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399']
          const color = colors[index % 5]

          return {
            name: cat,
            type: 'bar',
            data: validScores,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: color },
                { offset: 1, color: color + 'CC' }
              ]),
              borderRadius: [4, 4, 0, 0]
            },
            label: {
              show: true,
              position: 'top',
              formatter: (params) => {
                return formatScore(params.value)
              },
              fontSize: 10,
              fontWeight: 'bold'
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.3)'
              }
            },
            animationDelay: (idx) => idx * 50
          }
        }),
        animationEasing: 'elasticOut',
        animationDelayUpdate: (idx) => idx * 5
      }

      detailCvChart.setOption(option)
    }

    const handleDeleteModel = async (model) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除模型 "${model.model_id}" 吗？此操作不可恢复！`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        loading.value = true
        const response = await apiService.deleteModel(model.model_id)
        
        if (response.success) {
          ElMessage.success('模型删除成功')
          // 重新加载模型列表
          await loadModelList()
        } else {
          ElMessage.error(response.detail || '删除模型失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error(`删除模型失败: ${error.message || error}`)
        }
      } finally {
        loading.value = false
      }
    }

    onMounted(() => {
      loadModelList()
    })

    onBeforeUnmount(() => {
      if (accuracyChart) {
        accuracyChart.dispose()
        accuracyChart = null
      }
      if (aucChart) {
        aucChart.dispose()
        aucChart = null
      }
      if (radarChart) {
        radarChart.dispose()
        radarChart = null
      }
    })

    return {
      loading,
      modelList,
      detailVisible,
      currentModel,
      accuracyChartRef,
      aucChartRef,
      radarChartRef,
      detailCvChartRef,
      averageAccuracy,
      averageAUC,
      averageF1,
      cvScoresData,
      getModelTypeName,
      getModelTypeTag,
      formatMetric,
      formatScore,
      formatDate,
      primaryMetric,
      loadModelList,
      viewModelDetail,
      handleDeleteModel,
      handleDetailClose,
      getCvScoresForModel,
      getRowKey
    }
  }
}
</script>

<style scoped>
.dashboard.hc-page-shell {
  padding-top: 4px;
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
  transition: all 0.3s ease;
}

:deep(.el-card__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfc;
}

:deep(.el-card:hover) {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

:deep(.dashboard-model-table .el-table__inner-wrapper::before) {
  display: none;
}

:deep(.dashboard-model-table th.el-table__cell) {
  background: #f5f7fa !important;
  font-weight: 600;
  font-size: 13px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  height: 100%;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-right: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}

.metric-card {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-5px);
}

.metric-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
  font-weight: 500;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}

.metric-cv {
  font-size: 12px;
  color: #909399;
}

.confusion-matrix {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.confusion-table {
  border-collapse: collapse;
  font-size: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.confusion-table th,
.confusion-table td {
  padding: 15px 30px;
  text-align: center;
  border: 1px solid #e4e7ed;
}

.confusion-table th {
  background: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

.confusion-table tbody tr:nth-child(1) td:nth-child(2),
.confusion-table tbody tr:nth-child(2) td:nth-child(3) {
  background: #e1f3d8;
  font-weight: 600;
  color: #67c23a;
}

.confusion-table tbody tr:nth-child(1) td:nth-child(3),
.confusion-table tbody tr:nth-child(2) td:nth-child(2) {
  background: #fef0f0;
  font-weight: 600;
  color: #f56c6c;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  font-weight: 500;
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
  border-bottom: 2px solid #e4e7ed;
}

:deep(.el-table td) {
  border-bottom: 1px solid #f0f2f5;
}

:deep(.el-table__row:hover) {
  background: #f5f7fa;
}

:deep(.el-button) {
  border-radius: 6px;
  font-weight: 500;
}

:deep(.el-tag) {
  border-radius: 4px;
  font-weight: 500;
}

/* 展开行样式 */
.model-detail-expand {
  padding: 20px;
  background: #fafbfc;
}

.expand-section {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.expand-title {
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 10px;
  border-bottom: 2px solid #409eff;
}

.expand-metric-card {
  text-align: center;
  padding: 15px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s ease;
}

.expand-metric-card:hover {
  transform: translateY(-3px);
}

.expand-metric-hint {
  font-size: 12px;
  color: #909399;
  margin: -8px 0 14px 0;
  line-height: 1.5;
}

.expand-metric-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.expand-metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 6px;
}

.expand-metric-cv {
  font-size: 11px;
  color: #909399;
}

.confusion-matrix-small {
  display: flex;
  justify-content: center;
  padding: 15px;
}

.confusion-table-small {
  border-collapse: collapse;
  font-size: 14px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  overflow: hidden;
}

.confusion-table-small th,
.confusion-table-small td {
  padding: 12px 20px;
  text-align: center;
  border: 1px solid #e4e7ed;
}

.confusion-table-small th {
  background: #f5f7fa;
  font-weight: 600;
  color: #303133;
  font-size: 13px;
}

.confusion-table-small tbody tr:nth-child(1) td.correct,
.confusion-table-small tbody tr:nth-child(2) td.correct {
  background: #e1f3d8;
  font-weight: 600;
  color: #67c23a;
}

.confusion-table-small tbody tr:nth-child(1) td.error,
.confusion-table-small tbody tr:nth-child(2) td.error {
  background: #fef0f0;
  font-weight: 600;
  color: #f56c6c;
}
</style>

