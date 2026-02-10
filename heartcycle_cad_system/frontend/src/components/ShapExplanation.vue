<template>
  <div class="shap-explanation">
    <el-card v-if="globalImportance" class="shap-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div>
            <span style="font-weight: 600; font-size: 18px">全局特征重要性</span>
            <el-tag type="info" size="small" style="margin-left: 10px">模型整体解释</el-tag>
          </div>
          <div class="card-header-actions">
            <el-button
              size="small"
              :icon="Download"
              @click="exportGlobalData"
              circle
              title="导出数据"
            />
          </div>
        </div>
      </template>

      <!-- 使用新的特征重要性图表组件 -->
      <FeatureImportanceChart
        v-if="globalImportance.feature_importance"
        :feature-importance="globalImportance.feature_importance"
        title=""
        height="500px"
      />
      
      <!-- 全局特征重要性表格 -->
      <div style="margin-top: 30px">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px">
          <div style="display: flex; align-items: center; gap: 10px">
            <span style="font-weight: bold; color: #303133; font-size: 16px">特征重要性详细列表</span>
            <el-tooltip content="表格按重要性排序，显示所有特征的中文解释" placement="top">
              <el-icon style="color: #909399; cursor: help"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
          <div style="display: flex; gap: 8px">
            <el-input
              v-model="globalTableSearchText"
              placeholder="搜索特征名称或解释"
              clearable
              style="width: 250px"
              size="small"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button 
              size="small" 
              :icon="Download" 
              @click="exportGlobalTableData"
              title="导出表格数据"
            >
              导出
            </el-button>
          </div>
        </div>
        <el-table
          :data="filteredGlobalTableData"
          stripe
          border
          :max-height="500"
          highlight-current-row
          style="width: 100%"
        >
          <el-table-column type="index" label="排名" width="80" align="center" fixed="left">
            <template #default="{ $index }">
              <el-tag 
                :type="$index < 3 ? 'warning' : 'info'" 
                size="small"
                effect="dark"
                v-if="$index < 3"
              >
                {{ $index + 1 }}
              </el-tag>
              <span v-else>{{ $index + 1 }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="feature" label="特征名称" width="180" show-overflow-tooltip>
            <template #default="{ row, $index }">
              <span :style="{ fontWeight: $index < 3 ? 'bold' : 'normal', color: $index < 3 ? '#E6A23C' : '#606266' }">
                {{ row.feature }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="中文解释" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <div style="display: flex; align-items: center; gap: 5px">
                <span style="color: #303133">{{ row.description || getFeatureDescription(row.feature) }}</span>
                <el-tooltip :content="row.detail || getFeatureDetail(row.feature)" placement="right" effect="dark">
                  <el-icon style="color: #909399; cursor: help; font-size: 14px"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="importance" label="重要性" width="150" align="right" sortable default-sort="desc">
            <template #default="{ row, $index }">
              <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px">
                <el-progress
                  :percentage="row.importancePercentage"
                  :color="getImportanceColor($index)"
                  :stroke-width="8"
                  :show-text="false"
                  style="width: 80px; flex-shrink: 0"
                />
                <span 
                  :style="{ 
                    color: getImportanceColor($index),
                    fontWeight: 'bold',
                    fontSize: '13px',
                    minWidth: '60px',
                    textAlign: 'right'
                  }"
                >
                  {{ row.importance.toFixed(6) }}
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="重要性等级" width="120" align="center">
            <template #default="{ $index }">
              <el-tag 
                :type="getImportanceTagType($index)" 
                size="small"
                effect="dark"
              >
                {{ getImportanceLevel($index) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-card v-if="shapData" class="shap-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div>
            <span style="font-weight: 600; font-size: 18px">单样本预测解释</span>
            <el-tag :type="shapData.prediction === 1 ? 'danger' : 'success'" size="small" style="margin-left: 10px">
              {{ shapData.prediction === 1 ? '高风险' : '低风险' }}
            </el-tag>
          </div>
          <div class="card-header-actions">
            <el-button 
              size="small" 
              :icon="Download" 
              @click="exportInstanceData"
              circle
              title="导出数据"
            />
          </div>
        </div>
      </template>
      
      <div v-if="shapData.prediction !== undefined" class="prediction-info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="预测结果">
            <el-tag :type="shapData.prediction === 1 ? 'danger' : 'success'">
              {{ shapData.prediction === 1 ? '高风险 (1)' : '低风险 (0)' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            {{ (shapData.probability[shapData.prediction] * 100).toFixed(2) }}%
          </el-descriptions-item>
          <el-descriptions-item label="基础值" :span="2">
            {{ shapData.base_value.toFixed(4) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 使用新的SHAP瀑布图组件 -->
      <SHAPWaterfall
        v-if="shapData.shap_values && shapData.shap_values.length > 0"
        :shap-values="shapData.shap_values"
        :feature-values="shapData.feature_values"
        :feature-names="shapData.feature_names"
        :base-value="shapData.base_value"
        :prediction="shapData.probability[1]"
        title=""
        height="500px"
        style="margin-top: 20px"
      />

      <div style="margin-top: 20px">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px">
          <div style="display: flex; align-items: center; gap: 10px">
            <span style="font-weight: bold; color: #303133; font-size: 16px">详细特征贡献表</span>
            <el-tooltip content="表格按重要性排序，点击行可查看详情" placement="top">
              <el-icon style="color: #909399; cursor: help"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>
          <div style="display: flex; gap: 8px">
            <el-input
              v-model="tableSearchText"
              placeholder="搜索特征名称或中文解释"
              clearable
              style="width: 250px"
              size="small"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button 
              size="small" 
              :icon="Download" 
              @click="exportTableData"
              title="导出表格数据"
            >
              导出
            </el-button>
          </div>
        </div>
        <el-table
          :data="filteredShapTableData"
          stripe
          border
          :max-height="400"
          highlight-current-row
          @row-click="handleRowClick"
        >
          <el-table-column type="index" label="排名" width="70" align="center" />
          <el-table-column prop="feature" label="特征名称" min-width="220" show-overflow-tooltip>
            <template #default="{ row, $index }">
              <div style="display: flex; flex-direction: column; gap: 4px">
                <span :style="{ fontWeight: $index < 3 ? 'bold' : 'normal', color: $index < 3 ? '#E6A23C' : '#303133', fontSize: '14px' }">
                  {{ row.description || getFeatureDescription(row.feature) }}
                </span>
                <span style="color: #909399; font-size: 12px; font-weight: normal">
                  {{ row.feature }}
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="特征值" width="130" align="right">
            <template #default="{ row }">
              <span style="color: #606266">{{ row.value.toFixed(4) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="shapValue" label="SHAP（SHapley Additive exPlanations）值" width="200" align="right" sortable>
            <template #default="{ row }">
              <span 
                :style="{ 
                  color: row.shapValue >= 0 ? '#f56c6c' : '#67c23a',
                  fontWeight: 'bold',
                  fontSize: '13px'
                }"
              >
                {{ row.shapValue >= 0 ? '+' : '' }}{{ row.shapValue.toFixed(6) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="contribution" label="贡献方向" width="120" align="center">
            <template #default="{ row }">
              <el-tag 
                :type="row.shapValue >= 0 ? 'danger' : 'success'" 
                size="small"
                effect="dark"
              >
                <el-icon style="margin-right: 3px">
                  <component :is="row.shapValue >= 0 ? 'ArrowUp' : 'ArrowDown'" />
                </el-icon>
                {{ row.shapValue >= 0 ? '推高风险' : '降低风险' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="absShap" label="重要性" width="120" align="right" sortable default-sort="desc">
            <template #default="{ row }">
              <span style="color: #5470c6; font-weight: bold">
                {{ row.absShap.toFixed(6) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-empty v-if="!globalImportance && !shapData" description="暂无SHAP解释数据" />
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { Search, ArrowUp, ArrowDown, Download, InfoFilled } from '@element-plus/icons-vue'
import { getFeatureDescription, getFeatureDetail } from '../utils/featureDescriptions'
import FeatureImportanceChart from './charts/FeatureImportanceChart.vue'
import SHAPWaterfall from './charts/SHAPWaterfall.vue'

export default {
  name: 'ShapExplanation',
  components: {
    Search,
    ArrowUp,
    ArrowDown,
    Download,
    InfoFilled,
    FeatureImportanceChart,
    SHAPWaterfall
  },
  props: {
    globalImportance: {
      type: Object,
      default: null
    },
    shapData: {
      type: Object,
      default: null
    }
  },
  setup(props) {
    // 移除旧的图表ref，因为现在使用新的图表组件
    const shapTableData = ref([])
    const tableSearchText = ref('')
    const globalTableSearchText = ref('')
    const globalTableData = ref([])
    
    // 过滤后的表格数据
    const filteredShapTableData = computed(() => {
      if (!tableSearchText.value) {
        return shapTableData.value
      }
      const searchText = tableSearchText.value.toLowerCase()
      return shapTableData.value.filter(row => 
        row.feature.toLowerCase().includes(searchText)
      )
    })
    
    // 过滤后的全局特征重要性表格数据
    const filteredGlobalTableData = computed(() => {
      if (!globalTableSearchText.value) {
        return globalTableData.value
      }
      const searchText = globalTableSearchText.value.toLowerCase()
      return globalTableData.value.filter(row => 
        row.feature.toLowerCase().includes(searchText) ||
        row.description.toLowerCase().includes(searchText)
      )
    })
    
    // 获取重要性颜色
    const getImportanceColor = (index) => {
      if (index < 3) return '#E6A23C' // Top 3 金色
      if (index < 10) return '#409EFF' // Top 10 蓝色
      return '#909399' // 其他灰色
    }
    
    // 获取重要性标签类型
    const getImportanceTagType = (index) => {
      if (index < 3) return 'warning'
      if (index < 10) return 'primary'
      return 'info'
    }
    
    // 获取重要性等级
    const getImportanceLevel = (index) => {
      if (index < 3) return '极高'
      if (index < 10) return '高'
      if (index < 20) return '中'
      return '低'
    }
    
    // 处理行点击事件（可以用于高亮图表中的对应特征）
    const handleRowClick = (_row) => {
      // 可以在这里添加交互逻辑，比如高亮图表中的对应特征
      // 可选：添加提示信息
      // ElMessage.info(`特征: ${_row.feature}, SHAP值: ${_row.shapValue.toFixed(6)}`)
    }

    // 更新全局特征重要性表格数据
    const updateGlobalTableData = () => {
      if (!props.globalImportance) {
        globalTableData.value = []
        return
      }
      
      const featureRanking = props.globalImportance.feature_ranking || []
      if (featureRanking.length === 0) {
        globalTableData.value = []
        return
      }
      
      // 计算最大重要性值（用于百分比计算）
      const maxImportance = Math.max(...featureRanking.map(item => item.importance))
      
      globalTableData.value = featureRanking.map((item, index) => ({
        feature: item.feature,
        description: getFeatureDescription(item.feature),
        detail: getFeatureDetail(item.feature),
        importance: item.importance,
        importancePercentage: maxImportance > 0 ? (item.importance / maxImportance * 100) : 0,
        rank: index + 1
      }))
    }
    
    // 导出全局重要性数据
    const exportGlobalData = () => {
      if (!props.globalImportance) return
      const data = {
        类型: '全局特征重要性',
        时间: new Date().toLocaleString('zh-CN'),
        特征重要性: props.globalImportance.feature_ranking || []
      }
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `全局特征重要性_${new Date().getTime()}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    }
    
    // 导出全局特征重要性表格数据为CSV
    const exportGlobalTableData = () => {
      if (filteredGlobalTableData.value.length === 0) return
      
      // 构建CSV内容
      const headers = ['排名', '特征名称', '中文解释', '重要性', '重要性等级']
      const rows = filteredGlobalTableData.value.map((row) => [
        row.rank,
        row.feature,
        row.description,
        row.importance.toFixed(6),
        getImportanceLevel(row.rank - 1)
      ])
      
      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n')
      
      // 添加BOM以支持中文
      const BOM = '\uFEFF'
      const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `全局特征重要性表_${new Date().getTime()}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    }

    // 导出单样本解释数据
    const exportInstanceData = () => {
      if (!props.shapData) return
      const data = {
        类型: '单样本预测解释',
        时间: new Date().toLocaleString('zh-CN'),
        预测结果: props.shapData.prediction,
        预测概率: props.shapData.probability,
        基础值: props.shapData.base_value,
        特征贡献: shapTableData.value.map(item => ({
          特征名称: item.feature,
          特征值: item.value,
          SHAP值: item.shapValue,
          绝对SHAP值: item.absShap,
          贡献方向: item.shapValue >= 0 ? '推高风险' : '降低风险'
        }))
      }
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `单样本解释_${new Date().getTime()}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    }

    // 导出表格数据为CSV
    const exportTableData = () => {
      if (filteredShapTableData.value.length === 0) return
      
      // 构建CSV内容
      const headers = ['排名', '特征名称（英文）', '中文解释', '特征值', 'SHAP值', '绝对SHAP值', '贡献方向']
      const rows = filteredShapTableData.value.map((row, index) => [
        index + 1,
        row.feature,
        row.description || getFeatureDescription(row.feature),
        row.value.toFixed(4),
        row.shapValue.toFixed(6),
        row.absShap.toFixed(6),
        row.shapValue >= 0 ? '推高风险' : '降低风险'
      ])
      
      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n')
      
      // 添加BOM以支持中文
      const BOM = '\uFEFF'
      const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `特征贡献表_${new Date().getTime()}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    }

    // 更新表格数据
    // 更新表格数据
    const updateTableData = () => {
      if (!props.shapData) {
        shapTableData.value = []
        return
      }

      const { shap_values, feature_names, feature_values } = props.shapData

      shapTableData.value = feature_names.map((name, idx) => ({
        feature: name,
        description: getFeatureDescription(name),
        detail: getFeatureDetail(name),
        value: feature_values[idx],
        shapValue: shap_values[idx],
        absShap: Math.abs(shap_values[idx])
      })).sort((a, b) => b.absShap - a.absShap)
    }

    // 监听props变化，更新表格数据
    watch(
      () => props.globalImportance,
      () => {
        updateGlobalTableData()
      },
      { deep: true, immediate: true }
    )

    watch(
      () => props.shapData,
      () => {
        updateTableData()
      },
      { deep: true, immediate: true }
    )

    onMounted(() => {
      updateTableData()
      updateGlobalTableData()
    })

    return {
      shapTableData,
      tableSearchText,
      filteredShapTableData,
      globalTableData,
      globalTableSearchText,
      filteredGlobalTableData,
      handleRowClick,
      exportGlobalData,
      exportInstanceData,
      exportTableData,
      exportGlobalTableData,
      getImportanceColor,
      getImportanceTagType,
      getImportanceLevel,
      getFeatureDescription,
      getFeatureDetail,
      Download
    }
  }
}
</script>

<style scoped>
.shap-explanation {
  width: 100%;
}

.shap-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header-actions {
  display: flex;
  gap: 8px;
}

.chart-container {
  width: 100%;
}

.prediction-info {
  margin-bottom: 20px;
}

:deep(.el-table) {
  font-size: 13px;
}

:deep(.el-table__row) {
  cursor: pointer;
  transition: background-color 0.2s;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

:deep(.el-table .el-table__header-wrapper th) {
  background-color: #fafafa;
  font-weight: 600;
  color: #303133;
}

:deep(.el-progress-bar__outer) {
  border-radius: 4px;
}

:deep(.el-progress-bar__inner) {
  border-radius: 4px;
}

.h5-files-list {
  margin-top: 10px;
}
</style>

