<template>
  <div class="history">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon><Document /></el-icon>
          <span>历史记录</span>
          <div style="margin-left: auto; display: flex; gap: 10px; align-items: center">
            <el-tag type="info">共 {{ historyList.length }} 条</el-tag>
            <el-button
              type="danger"
              size="default"
              :disabled="selectedRows.length === 0"
              @click="handleBatchDelete"
            >
              <el-icon><Delete /></el-icon>
              批量删除 ({{ selectedRows.length }})
            </el-button>
            <el-button
              type="warning"
              size="default"
              @click="handleClearAll"
            >
              <el-icon><DeleteFilled /></el-icon>
              清空全部
            </el-button>
            <el-button
              type="primary"
              size="default"
              @click="loadHistory"
            >
              <el-icon><Refresh /></el-icon>
              刷新列表
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="historyList"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="索引" width="80" sortable>
          <template #default="scope">
            <el-tag type="info" size="small">#{{ scope.row.id }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="时间" width="180" sortable>
          <template #default="scope">
            <div>
              <div>{{ scope.row.date }}</div>
              <div style="font-size: 12px; color: #909399">
                {{ formatTimestamp(scope.row.timestamp) }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="100" />
        <el-table-column prop="gender" label="性别" width="100">
          <template #default="scope">
            {{ scope.row.gender === 'M' ? '男' : '女' }}
          </template>
        </el-table-column>
        <el-table-column prop="bmi" label="BMI" width="100" />
        <el-table-column prop="riskScore" label="风险评分" width="120" sortable>
          <template #default="scope">
            <el-tag :type="getRiskType(scope.row.riskScore)">
              {{ scope.row.riskScore }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="prediction" label="预测结果" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.prediction === 1 ? 'danger' : 'success'">
              {{ scope.row.prediction === 1 ? '高风险' : '低风险' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="scope">
            {{ scope.row.confidence ? (scope.row.confidence * 100).toFixed(1) + '%' : 'N/A' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="viewDetail(scope.row)"
              plain
            >
              <el-icon><ViewIcon /></el-icon>
              查看详情
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(scope.row)"
              plain
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && historyList.length === 0" description="暂无历史记录" />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="分析详情"
      width="900px"
    >
      <div v-if="currentDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="记录ID">
            <el-tag type="info">#{{ currentDetail.id }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="分析时间">
            {{ currentDetail.date }}
            <div style="font-size: 12px; color: #909399; margin-top: 4px">
              时间戳: {{ currentDetail.timestamp }}
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="年龄">{{ currentDetail.age }}</el-descriptions-item>
          <el-descriptions-item label="性别">
            {{ currentDetail.gender === 'M' ? '男' : '女' }}
          </el-descriptions-item>
          <el-descriptions-item label="身高 (cm)">{{ currentDetail.height }}</el-descriptions-item>
          <el-descriptions-item label="体重 (kg)">{{ currentDetail.weight }}</el-descriptions-item>
          <el-descriptions-item label="BMI">{{ currentDetail.bmi?.toFixed(2) || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="使用的模型">
            {{ currentDetail.modelId || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="风险评分" :span="2">
            <el-tag :type="getRiskType(currentDetail.riskScore)" size="large">
              {{ currentDetail.riskScore }}%
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预测结果" :span="2">
            <el-tag :type="currentDetail.prediction === 1 ? 'danger' : 'success'" size="large">
              {{ currentDetail.prediction === 1 ? '高风险' : '低风险' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预测置信度">
            {{ currentDetail.confidence ? (currentDetail.confidence * 100).toFixed(2) + '%' : 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="类别0概率">
            {{ currentDetail.probability && currentDetail.probability[0] ? (currentDetail.probability[0] * 100).toFixed(2) + '%' : 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="类别1概率">
            {{ currentDetail.probability && currentDetail.probability[1] ? (currentDetail.probability[1] * 100).toFixed(2) + '%' : 'N/A' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- HRV特征 -->
        <el-divider>HRV特征</el-divider>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="平均RR间期 (ms)">
            {{ currentDetail.mean_rr || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="SDNN (ms)">
            {{ currentDetail.sdnn || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="RMSSD (ms)">
            {{ currentDetail.rmssd || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="pNN50 (%)">
            {{ currentDetail.pnn50 || 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="LF/HF比值">
            {{ currentDetail.lf_hf_ratio || 'N/A' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { Document, Delete, DeleteFilled, Refresh, View as ViewIcon } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storage } from '../utils/storage'

export default {
  name: 'History',
  components: {
    Document,
    Delete,
    DeleteFilled,
    Refresh,
    ViewIcon
  },
  setup() {
    const loading = ref(false)
    const historyList = ref([])
    const detailVisible = ref(false)
    const currentDetail = ref(null)
    const selectedRows = ref([])

    // 从localStorage加载历史记录
    const loadHistory = () => {
      loading.value = true
      try {
        historyList.value = storage.getHistory()
        // 按时间戳倒序排列（最新的在前）
        historyList.value.sort((a, b) => {
          const timeA = a.timestamp || new Date(a.date || 0).getTime()
          const timeB = b.timestamp || new Date(b.date || 0).getTime()
          return timeB - timeA
        })
        ElMessage.success(`已加载 ${historyList.value.length} 条记录`)
      } catch (error) {
        ElMessage.error('加载历史记录失败: ' + error.message)
      } finally {
        loading.value = false
      }
    }

    const getRiskType = (score) => {
      const numScore = parseFloat(score)
      if (numScore < 30) return 'success'
      if (numScore < 60) return 'warning'
      return 'danger'
    }

    const formatTimestamp = (timestamp) => {
      if (!timestamp) return 'N/A'
      const date = new Date(timestamp)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }

    const viewDetail = (row) => {
      currentDetail.value = row
      detailVisible.value = true
    }

    const handleDelete = async (row) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除记录 #${row.id} 吗？`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        if (storage.deleteHistory(row.id)) {
          ElMessage.success('删除成功')
          loadHistory()
        } else {
          ElMessage.error('删除失败')
        }
      } catch (error) {
        // 用户取消
      }
    }

    const handleSelectionChange = (selection) => {
      selectedRows.value = selection
    }

    const handleBatchDelete = async () => {
      if (selectedRows.value.length === 0) {
        ElMessage.warning('请先选择要删除的记录')
        return
      }

      try {
        await ElMessageBox.confirm(
          `确定要删除选中的 ${selectedRows.value.length} 条记录吗？`,
          '确认批量删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        const ids = selectedRows.value.map(row => row.id)
        if (storage.deleteHistoryBatch(ids)) {
          ElMessage.success(`成功删除 ${ids.length} 条记录`)
          selectedRows.value = []
          loadHistory()
        } else {
          ElMessage.error('批量删除失败')
        }
      } catch (error) {
        // 用户取消
      }
    }

    const handleClearAll = async () => {
      if (historyList.value.length === 0) {
        ElMessage.warning('没有可清空的记录')
        return
      }

      try {
        await ElMessageBox.confirm(
          `确定要清空所有 ${historyList.value.length} 条记录吗？此操作不可恢复！`,
          '确认清空',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        if (storage.clearHistory()) {
          ElMessage.success('已清空所有记录')
          historyList.value = []
          selectedRows.value = []
        } else {
          ElMessage.error('清空失败')
        }
      } catch (error) {
        // 用户取消
      }
    }

    onMounted(() => {
      loadHistory()
    })

    return {
      loading,
      historyList,
      detailVisible,
      currentDetail,
      selectedRows,
      getRiskType,
      formatTimestamp,
      viewDetail,
      handleDelete,
      handleSelectionChange,
      handleBatchDelete,
      handleClearAll,
      loadHistory
    }
  }
}
</script>

<style scoped>
.history {
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

.history {
  max-width: 1400px;
  margin: 0 auto;
}
</style>

