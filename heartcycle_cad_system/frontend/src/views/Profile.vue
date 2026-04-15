<template>
  <div class="profile-container hc-page-shell">
    <el-card class="profile-card hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>个人资料</span>
        </div>
      </template>

      <div class="profile-content" v-if="user">
        <div class="avatar-section">
          <el-avatar :size="100" :src="user.avatar_url">
            {{ user.full_name?.charAt(0) || user.username?.charAt(0) }}
          </el-avatar>
          <div class="user-info">
            <h2>{{ user.full_name || user.username }}</h2>
            <el-tag :type="roleTagType">{{ roleLabel }}</el-tag>
          </div>
        </div>

        <el-divider />

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="100px"
          label-position="left"
        >
          <el-form-item label="用户名">
            <el-input v-model="user.username" disabled />
          </el-form-item>

          <el-form-item label="邮箱">
            <el-input v-model="user.email" disabled />
          </el-form-item>

          <el-form-item label="姓名" prop="full_name">
            <el-input v-model="form.full_name" placeholder="请输入姓名" />
          </el-form-item>

          <el-form-item label="手机号" prop="phone">
            <el-input v-model="form.phone" placeholder="请输入手机号" />
          </el-form-item>

          <el-form-item label="科室" prop="department" v-if="user.role === 'doctor'">
            <el-input v-model="form.department" placeholder="请输入科室" />
          </el-form-item>

          <el-form-item label="医院" prop="hospital" v-if="user.role === 'doctor'">
            <el-input v-model="form.hospital" placeholder="请输入医院" />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleUpdate" :loading="loading">
              保存修改
            </el-button>
          </el-form-item>
        </el-form>

        <el-divider />

        <h3>修改密码</h3>
        <el-form
          ref="passwordFormRef"
          :model="passwordForm"
          :rules="passwordRules"
          label-width="100px"
          label-position="left"
        >
          <el-form-item label="原密码" prop="old_password">
            <el-input
              v-model="passwordForm.old_password"
              type="password"
              placeholder="请输入原密码"
              show-password
            />
          </el-form-item>

          <el-form-item label="新密码" prop="new_password">
            <el-input
              v-model="passwordForm.new_password"
              type="password"
              placeholder="请输入新密码（至少6位）"
              show-password
            />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirm_password">
            <el-input
              v-model="passwordForm.confirm_password"
              type="password"
              placeholder="请再次输入新密码"
              show-password
            />
          </el-form-item>

          <el-form-item>
            <el-button type="warning" @click="handleChangePassword" :loading="passwordLoading">
              修改密码
            </el-button>
          </el-form-item>
        </el-form>

        <el-divider />

        <el-descriptions title="账号与角色标识" :column="1" border size="small" class="account-ids-block">
          <el-descriptions-item label="用户 ID（主键）">{{ user.id }}</el-descriptions-item>
          <el-descriptions-item label="角色类型 ID">
            {{ user.role_type_id != null ? user.role_type_id : '—' }}
            <span class="account-ids-hint">（与用户主键独立：1 管理员 2 医生 3 科研 4 患者）</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="user.role === 'patient'" label="关联患者档案 ID">
            {{ user.linked_patient_id != null ? user.linked_patient_id : '—' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="account-info">
          <p><strong>注册时间：</strong>{{ formatDate(user.created_at) }}</p>
          <p><strong>最后登录：</strong>{{ formatDate(user.last_login) }}</p>
        </div>

        <el-button type="danger" @click="handleLogout" style="margin-top: 20px">
          退出登录
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/services/api'

const router = useRouter()

const user = ref(null)
const loading = ref(false)
const passwordLoading = ref(false)
const formRef = ref(null)
const passwordFormRef = ref(null)

const form = reactive({
  full_name: '',
  phone: '',
  department: '',
  hospital: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const rules = {
  full_name: [
    { max: 100, message: '姓名最多100个字符', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号', trigger: 'blur' }
  ]
}

const passwordRules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const roleLabel = computed(() => {
  const roles = {
    admin: '管理员',
    doctor: '医生',
    patient: '患者',
    researcher: '研究人员'
  }
  return roles[user.value?.role] || user.value?.role
})

const roleTagType = computed(() => {
  const types = {
    admin: 'danger',
    doctor: 'success',
    patient: 'info',
    researcher: 'warning'
  }
  return types[user.value?.role] || 'info'
})

const formatDate = (dateStr) => {
  if (!dateStr) return '未知'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadUser = async () => {
  try {
    const response = await authApi.getCurrentUser()
    if (response.success) {
      user.value = response.data
      form.full_name = user.value.full_name || ''
      form.phone = user.value.phone || ''
      form.department = user.value.department || ''
      form.hospital = user.value.hospital || ''
    }
  } catch (error) {
    ElMessage.error('获取用户信息失败')
  }
}

const handleUpdate = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const response = await authApi.updateProfile(form)
      if (response.success) {
        ElMessage.success('更新成功')
        user.value = response.data
        localStorage.setItem('user', JSON.stringify(response.data))
      }
    } catch (error) {
      ElMessage.error('更新失败')
    } finally {
      loading.value = false
    }
  })
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return

    passwordLoading.value = true
    try {
      const response = await authApi.changePassword(passwordForm)
      if (response.success) {
        ElMessage.success('密码修改成功，请重新登录')
        passwordFormRef.value.resetFields()
        handleLogout()
      }
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '密码修改失败')
    } finally {
      passwordLoading.value = false
    }
  })
}

const handleLogout = async () => {
  try {
    await authApi.logout()
  } catch (error) {
    // 忽略登出错误
  }

  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')

  ElMessage.success('已退出登录')
  router.push('/login')
}

onMounted(() => {
  loadUser()
})
</script>

<style scoped>
.profile-container.hc-page-shell {
  max-width: 800px;
  padding-top: 8px;
}

.profile-card {
  border-radius: var(--hc-radius-lg, 12px);
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.user-info h2 {
  margin: 0 0 10px 0;
}

.account-ids-block {
  margin-bottom: 20px;
}

.account-ids-hint {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.account-info p {
  margin: 8px 0;
  color: #606266;
}

h3 {
  margin-bottom: 20px;
  color: #303133;
}
</style>
