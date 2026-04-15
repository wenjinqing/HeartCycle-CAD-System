<template>
  <div class="users-container hc-page-shell">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-select v-model="roleFilter" placeholder="筛选角色" clearable style="width: 150px">
            <el-option label="全部" value="" />
            <el-option label="管理员" value="admin" />
            <el-option label="医生" value="doctor" />
            <el-option label="患者" value="patient" />
            <el-option label="研究人员" value="researcher" />
          </el-select>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">{{ getRoleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '正常' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="180">
          <template #default="{ row }">
            {{ formatDate(row.last_login) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.is_active && row.role !== 'admin'"
              type="danger"
              size="small"
              @click="handleDeactivate(row)"
            >
              禁用
            </el-button>
            <el-button
              v-if="!row.is_active"
              type="success"
              size="small"
              @click="handleActivate(row)"
            >
              启用
            </el-button>
            <el-button
              v-if="row.role !== 'admin'"
              type="primary"
              size="small"
              @click="handleResetPassword(row)"
            >
              重置密码
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadUsers"
          @current-change="loadUsers"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authApi } from '@/services/api'

const users = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const roleFilter = ref('')

const getRoleLabel = (role) => {
  const roles = {
    admin: '管理员',
    doctor: '医生',
    patient: '患者',
    researcher: '研究人员'
  }
  return roles[role] || role
}

const getRoleTagType = (role) => {
  const types = {
    admin: 'danger',
    doctor: 'success',
    patient: 'info',
    researcher: 'warning'
  }
  return types[role] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await authApi.getUsers({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      role: roleFilter.value || undefined
    })
    if (response.success) {
      users.value = response.data.items
      total.value = response.data.total
    }
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleDeactivate = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要禁用用户 "${user.username}" 吗？`,
      '确认禁用',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await authApi.deactivateUser(user.id)
    if (response.success) {
      ElMessage.success('用户已禁用')
      loadUsers()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleActivate = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要启用用户 "${user.username}" 吗？`,
      '确认启用',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'success'
      }
    )

    const response = await authApi.activateUser(user.id)
    if (response.success) {
      ElMessage.success('用户已启用')
      loadUsers()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleResetPassword = async (user) => {
  try {
    const { value: newPassword } = await ElMessageBox.prompt(
      `请输入用户 "${user.username}" 的新密码`,
      '重置密码',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPattern: /^.{6,}$/,
        inputErrorMessage: '密码长度至少6位',
        inputPlaceholder: '请输入新密码（至少6位）',
        inputType: 'password'
      }
    )

    if (!newPassword) {
      ElMessage.warning('密码不能为空')
      return
    }

    const response = await authApi.resetUserPassword(user.id, newPassword)
    if (response.success) {
      ElMessage.success(`密码已重置为: ${newPassword}`)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

watch(roleFilter, () => {
  currentPage.value = 1
  loadUsers()
})

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users-container {
  padding-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
