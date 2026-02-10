<template>
  <el-card class="prediction-details-card">
    <template #header>
      <div class="card-header-with-actions">
        <div>
          <span style="font-weight: 600; font-size: 18px">预测详情</span>
          <el-tag v-if="result.method === 'ensemble'" type="info" style="margin-left: 10px">
            集成预测（{{ result.method === 'voting' ? '投票' : '加权平均' }}）
          </el-tag>
        </div>
        <div class="card-actions">
          <el-button
            size="small"
            :icon="Document"
            @click="$emit('export-json')"
            circle
            title="导出JSON"
          />
          <el-button
            size="small"
            type="primary"
            :icon="Document"
            @click="$emit('export-pdf')"
            circle
            title="导出PDF报告"
          />
          <el-button
            size="small"
            :icon="Printer"
            @click="$emit('print')"
            circle
            title="打印结果"
          />
        </div>
      </div>
    </template>

    <el-descriptions :column="2" border>
      <el-descriptions-item label="预测方法">
        {{ result.method === 'ensemble' ? '模型集成' : '单个模型' }}
        <el-tag v-if="result.method === 'ensemble'" type="info" size="small" style="margin-left: 10px">
          {{ result.modelCount }} 个模型
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="预测类别">
        <el-tag :type="result.prediction === 1 ? 'danger' : 'success'">
          {{ result.prediction === 1 ? '高风险' : '低风险' }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="预测置信度">
        {{ (result.confidence * 100).toFixed(2) }}%
      </el-descriptions-item>
      <el-descriptions-item v-if="result.agreement !== undefined" label="模型一致性">
        {{ (result.agreement * 100).toFixed(1) }}%
        <el-tag :type="agreementType" size="small" style="margin-left: 10px">
          {{ agreementText }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="类别0概率">
        {{ (result.probability[0] * 100).toFixed(2) }}%
      </el-descriptions-item>
      <el-descriptions-item label="类别1概率">
        {{ (result.probability[1] * 100).toFixed(2) }}%
      </el-descriptions-item>
      <el-descriptions-item v-if="result.individualPredictions" label="各模型预测" :span="2">
        <div style="display: flex; gap: 8px; flex-wrap: wrap">
          <el-tag
            v-for="(pred, index) in result.individualPredictions"
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
</template>

<script>
import { computed } from 'vue'
import { Document, Printer } from '@element-plus/icons-vue'

export default {
  name: 'PredictionDetails',
  props: {
    result: {
      type: Object,
      required: true
    }
  },
  emits: ['export-json', 'export-pdf', 'print'],
  setup(props) {
    const agreementType = computed(() => {
      if (!props.result.agreement) return 'info'
      return props.result.agreement > 0.8 ? 'success' : (props.result.agreement > 0.5 ? 'warning' : 'danger')
    })

    const agreementText = computed(() => {
      if (!props.result.agreement) return ''
      return props.result.agreement > 0.8 ? '高度一致' : (props.result.agreement > 0.5 ? '中等一致' : '存在分歧')
    })

    return {
      Document,
      Printer,
      agreementType,
      agreementText
    }
  }
}
</script>

<style scoped>
.prediction-details-card {
  border-radius: 8px;
}

.prediction-details-card :deep(.el-card__header) {
  padding: 18px 20px;
  border-bottom: 2px solid #f0f2f5;
}

.card-header-with-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-actions {
  display: flex;
  gap: 8px;
}

:deep(.el-descriptions) {
  margin-top: 10px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
}

@media print {
  .card-actions {
    display: none;
  }
}
</style>
