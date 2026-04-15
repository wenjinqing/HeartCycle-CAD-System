<template>
  <div class="audit-logs-container hc-page-shell">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <div class="filters">
            <el-select v-model="actionFilter" placeholder="操作类型" clearable style="width: 150px">
              <el-option label="全部" value="" />
              <el-option label="登录" value="login" />
              <el-option label="登出" value="logout" />
              <el-option label="注册" value="register" />
              <el-option label="修改密码" value="change_password" />
              <el-option label="禁用用户" value="deactivate_user" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="user_id" label="用户ID" width="100" />
        <el-table-column prop="action" label="操作" width="120">
          <template #default="{ row }">
            <el-tag :type="getActionTagType(row.action)">{{ getActionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource" label="资源" width="100" />
        <el-table-column prop="resource_id" label="资源ID" width="100" />
        <el-table-column prop="ip_address" label="IP地址" width="150" />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="details" label="详情" min-width="200">
          <template #default="{ row }">
            <el-tooltip v-if="row.details" :content="row.details" placement="top">
              <span class="details-text">{{ row.details }}</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/services/api'

const logs = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const actionFilter = ref('')

const getActionLabel = (action) => {
  const actions = {
    login: '登录',
    logout: '登出',
    register: '注册',
    change_password: '修改密码',
    deactivate_user: '禁用用户'
  }
  return actions[action] || action
}

const getActionTagType = (action) => {
  const types = {
    login: 'success',
    logout: 'info',
    register: 'primary',
    change_password: 'warning',
    deactivate_user: 'danger'
  }
  return types[action] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadLogs = async () => {
  loading.value = true
  try {
    const response = await authApi.getAuditLogs({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      action: actionFilter.value || undefined
    })
    if (response.success) {
      logs.value = response.data.items
      total.value = response.data.total
    }
  } catch (error) {
    ElMessage.error('获取审计日志失败')
  } finally {
    loading.value = false
  }
}

watch(actionFilter, () => {
  currentPage.value = 1
  loadLogs()
})

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.audit-logs-container {
  padding-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.details-text {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}
</style>
