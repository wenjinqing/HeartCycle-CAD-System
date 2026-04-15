<template>
  <div class="patient-list hc-page-shell">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>患者管理</span>
          <el-button
            v-if="userRole === 'doctor' || userRole === 'admin'"
            type="primary"
            @click="showAddDialog = true"
          >
            <el-icon><Plus /></el-icon>
            添加患者
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" class="search-form">
        <el-form-item label="搜索">
          <el-input
            v-model="searchQuery"
            placeholder="姓名、患者编号、手机号"
            clearable
            @clear="loadPatients"
            @keyup.enter="loadPatients"
          >
            <template #append>
              <el-button :icon="Search" @click="loadPatients" />
            </template>
          </el-input>
        </el-form-item>
      </el-form>

      <!-- 患者列表 -->
      <el-table
        :data="patients"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="patient_no" label="患者编号" width="150" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="gender" label="性别" width="80">
          <template #default="{ row }">
            {{ row.gender === 'male' ? '男' : '女' }}
          </template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="80" />
        <el-table-column label="手机号" width="168">
          <template #default="{ row }">
            <span>{{ phoneDisplay(row) }}</span>
            <el-button
              v-if="row.phone"
              type="primary"
              link
              size="small"
              class="phone-toggle"
              @click.stop="togglePhoneReveal(row.id)"
            >
              {{ phoneRevealMap[row.id] ? '隐藏' : '显示' }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="doctor_name" label="主治医生" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="viewPatient(row.id)"
              link
            >
              查看
            </el-button>
            <el-button
              v-if="canEdit(row)"
              type="warning"
              size="small"
              @click="editPatient(row)"
              link
            >
              编辑
            </el-button>
            <el-button
              v-if="canDelete(row)"
              type="danger"
              size="small"
              @click="deletePatient(row)"
              link
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadPatients"
        @current-change="loadPatients"
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <!-- 添加/编辑患者对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingPatient ? '编辑患者' : '添加患者'"
      width="820px"
      top="4vh"
    >
      <el-scrollbar max-height="72vh">
      <el-form
        :model="patientForm"
        :rules="formRules"
        ref="patientFormRef"
        label-width="120px"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="patientForm.name" placeholder="请输入姓名" />
        </el-form-item>

        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="patientForm.gender">
            <el-radio label="male">男</el-radio>
            <el-radio label="female">女</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="年龄" prop="age">
          <el-input-number
            v-model="patientForm.age"
            :min="0"
            :max="150"
            placeholder="请输入年龄"
          />
        </el-form-item>

        <el-form-item label="出生日期" prop="birth_date">
          <el-date-picker
            v-model="patientForm.birth_date"
            type="date"
            placeholder="选择出生日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input v-model="patientForm.phone" placeholder="请输入手机号" />
        </el-form-item>

        <el-divider content-position="left">体征与职业（可选，用于监测分析自动填入）</el-divider>

        <el-form-item label="职业" prop="occupation">
          <el-input v-model="patientForm.occupation" placeholder="选填" maxlength="100" show-word-limit />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="身高(cm)" prop="height_cm">
              <el-input-number
                v-model="patientForm.height_cm"
                :min="0"
                :max="300"
                :precision="1"
                placeholder="cm"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="体重(kg)" prop="weight_kg">
              <el-input-number
                v-model="patientForm.weight_kg"
                :min="0"
                :max="500"
                :precision="1"
                placeholder="kg"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="收缩压" prop="blood_pressure_systolic">
              <el-input-number
                v-model="patientForm.blood_pressure_systolic"
                :min="0"
                :max="300"
                placeholder="mmHg"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="舒张压" prop="blood_pressure_diastolic">
              <el-input-number
                v-model="patientForm.blood_pressure_diastolic"
                :min="0"
                :max="200"
                placeholder="mmHg"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="静息心率" prop="resting_heart_rate">
              <el-input-number
                v-model="patientForm.resting_heart_rate"
                :min="0"
                :max="300"
                placeholder="次/分"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">HRV 指标（可选，与监测页一致）</el-divider>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="平均RR(ms)" prop="hrv_mean_rr">
              <el-input-number v-model="patientForm.hrv_mean_rr" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="SDNN" prop="hrv_sdnn">
              <el-input-number v-model="patientForm.hrv_sdnn" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="RMSSD" prop="hrv_rmssd">
              <el-input-number v-model="patientForm.hrv_rmssd" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="pNN50(%)" prop="hrv_pnn50">
              <el-input-number v-model="patientForm.hrv_pnn50" :min="0" :max="100" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="LF/HF" prop="hrv_lf_hf_ratio">
          <el-input-number v-model="patientForm.hrv_lf_hf_ratio" :min="0" :precision="2" style="width: 280px" />
        </el-form-item>

        <el-divider content-position="left">腰围与实验室（可选，与监测页一致）</el-divider>
        <el-form-item label="腰围(cm)" prop="waist_cm">
          <el-input-number v-model="patientForm.waist_cm" :min="0" :max="200" :precision="1" style="width: 220px" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="总胆固醇" prop="total_cholesterol">
              <el-input-number v-model="patientForm.total_cholesterol" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="LDL-C" prop="ldl_cholesterol">
              <el-input-number v-model="patientForm.ldl_cholesterol" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="HDL-C" prop="hdl_cholesterol">
              <el-input-number v-model="patientForm.hdl_cholesterol" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="甘油三酯" prop="triglyceride">
              <el-input-number v-model="patientForm.triglyceride" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="空腹血糖" prop="fasting_glucose">
              <el-input-number v-model="patientForm.fasting_glucose" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="HbA1c(%)" prop="hba1c">
              <el-input-number v-model="patientForm.hba1c" :min="0" :max="20" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">生活方式与危险因素</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="吸烟" prop="smoke_status">
              <el-select v-model="patientForm.smoke_status" placeholder="请选择" style="width: 100%">
                <el-option label="从不" value="never" />
                <el-option label="已戒" value="former" />
                <el-option label="目前吸烟" value="current" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="体力活动" prop="physical_activity">
              <el-select v-model="patientForm.physical_activity" placeholder="请选择" style="width: 100%">
                <el-option label="不详" value="unknown" />
                <el-option label="久坐少动" value="sedentary" />
                <el-option label="轻度" value="light" />
                <el-option label="中度" value="moderate" />
                <el-option label="重度" value="heavy" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="危险因素">
          <div class="patient-risk-switches">
            <el-switch v-model="patientForm.diabetes" :active-value="1" :inactive-value="0" active-text="糖尿病" />
            <el-switch v-model="patientForm.hypertension_dx" :active-value="1" :inactive-value="0" active-text="高血压" />
            <el-switch v-model="patientForm.dyslipidemia" :active-value="1" :inactive-value="0" active-text="血脂异常" />
            <el-switch v-model="patientForm.family_history_cad" :active-value="1" :inactive-value="0" active-text="早发冠心病家族史" />
            <el-switch v-model="patientForm.chest_pain_symptom" :active-value="1" :inactive-value="0" active-text="胸痛/心绞痛" />
          </div>
        </el-form-item>

        <el-form-item label="地址" prop="address">
          <el-input
            v-model="patientForm.address"
            type="textarea"
            :rows="2"
            placeholder="请输入地址"
          />
        </el-form-item>

        <el-form-item label="紧急联系人" prop="emergency_contact">
          <el-input v-model="patientForm.emergency_contact" placeholder="请输入紧急联系人" />
        </el-form-item>

        <el-form-item label="紧急联系电话" prop="emergency_phone">
          <el-input v-model="patientForm.emergency_phone" placeholder="请输入紧急联系电话" />
        </el-form-item>

        <el-form-item label="病史" prop="medical_history">
          <el-input
            v-model="patientForm.medical_history"
            type="textarea"
            :rows="3"
            placeholder="请输入病史"
          />
        </el-form-item>

        <el-form-item label="过敏史" prop="allergies">
          <el-input
            v-model="patientForm.allergies"
            type="textarea"
            :rows="2"
            placeholder="请输入过敏史"
          />
        </el-form-item>

        <el-form-item label="备注" prop="notes">
          <el-input
            v-model="patientForm.notes"
            type="textarea"
            :rows="2"
            placeholder="请输入备注"
          />
        </el-form-item>
      </el-form>
      </el-scrollbar>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitPatient" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import { api } from '@/services/api'
import { maskPhone } from '@/utils/phonePrivacy'

const router = useRouter()

// 用户角色
const userRole = computed(() => {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  return user.role || 'patient'
})

// 数据
const patients = ref([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框
const showAddDialog = ref(false)
const editingPatient = ref(null)
const submitting = ref(false)
const patientFormRef = ref(null)

// 表单数据
const phoneRevealMap = reactive({})

const patientForm = reactive({
  name: '',
  gender: 'male',
  age: null,
  birth_date: '',
  phone: '',
  occupation: '',
  height_cm: null,
  weight_kg: null,
  blood_pressure_systolic: null,
  blood_pressure_diastolic: null,
  resting_heart_rate: null,
  hrv_mean_rr: null,
  hrv_sdnn: null,
  hrv_rmssd: null,
  hrv_pnn50: null,
  hrv_lf_hf_ratio: null,
  waist_cm: null,
  total_cholesterol: null,
  ldl_cholesterol: null,
  hdl_cholesterol: null,
  triglyceride: null,
  fasting_glucose: null,
  hba1c: null,
  smoke_status: 'never',
  physical_activity: 'unknown',
  diabetes: 0,
  hypertension_dx: 0,
  dyslipidemia: 0,
  family_history_cad: 0,
  chest_pain_symptom: 0,
  address: '',
  emergency_contact: '',
  emergency_phone: '',
  medical_history: '',
  allergies: '',
  notes: ''
})

/** 提交前清理：空字符串的出生日期会导致后端 datetime 校验失败 */
const buildPatientPayload = () => {
  const p = { ...patientForm }
  if (p.birth_date === '' || p.birth_date == null) {
    delete p.birth_date
  }
  return p
}

const formatSubmitError = (error) => {
  const d = error?.response?.data?.detail
  if (Array.isArray(d)) {
    return d.map((e) => e.msg || e.message || JSON.stringify(e)).join('; ')
  }
  if (typeof d === 'string') return d
  if (d && typeof d === 'object') return JSON.stringify(d)
  return error?.message || '请求失败'
}

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  gender: [
    { required: true, message: '请选择性别', trigger: 'change' }
  ],
  phone: [
    {
      validator: (_rule, value, callback) => {
        if (!value || String(value).trim() === '') {
          callback()
          return
        }
        if (!/^1[3-9]\d{9}$/.test(String(value))) {
          callback(new Error('请输入正确的手机号'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

// 加载患者列表
const phoneDisplay = (row) => {
  if (!row?.phone) return '-'
  return phoneRevealMap[row.id] ? row.phone : maskPhone(row.phone)
}

const togglePhoneReveal = (id) => {
  phoneRevealMap[id] = !phoneRevealMap[id]
}

const loadPatients = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }
    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    const response = await api.get('/patients', { params })

    if (response.success) {
      patients.value = response.data.items
      total.value = response.data.total
    }
  } catch (error) {
    ElMessage.error('加载患者列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 查看患者详情
const viewPatient = (patientId) => {
  router.push(`/patients/${patientId}`)
}

// 编辑患者
const editPatient = (patient) => {
  editingPatient.value = patient
  Object.assign(patientForm, {
    name: patient.name,
    gender: patient.gender,
    age: patient.age,
    birth_date: patient.birth_date,
    phone: patient.phone,
    occupation: patient.occupation ?? '',
    height_cm: patient.height_cm ?? null,
    weight_kg: patient.weight_kg ?? null,
    blood_pressure_systolic: patient.blood_pressure_systolic ?? null,
    blood_pressure_diastolic: patient.blood_pressure_diastolic ?? null,
    resting_heart_rate: patient.resting_heart_rate ?? null,
    hrv_mean_rr: patient.hrv_mean_rr ?? null,
    hrv_sdnn: patient.hrv_sdnn ?? null,
    hrv_rmssd: patient.hrv_rmssd ?? null,
    hrv_pnn50: patient.hrv_pnn50 ?? null,
    hrv_lf_hf_ratio: patient.hrv_lf_hf_ratio ?? null,
    waist_cm: patient.waist_cm ?? null,
    total_cholesterol: patient.total_cholesterol ?? null,
    ldl_cholesterol: patient.ldl_cholesterol ?? null,
    hdl_cholesterol: patient.hdl_cholesterol ?? null,
    triglyceride: patient.triglyceride ?? null,
    fasting_glucose: patient.fasting_glucose ?? null,
    hba1c: patient.hba1c ?? null,
    smoke_status: patient.smoke_status || 'never',
    physical_activity: patient.physical_activity || 'unknown',
    diabetes: patient.diabetes === 1 ? 1 : 0,
    hypertension_dx: patient.hypertension_dx === 1 ? 1 : 0,
    dyslipidemia: patient.dyslipidemia === 1 ? 1 : 0,
    family_history_cad: patient.family_history_cad === 1 ? 1 : 0,
    chest_pain_symptom: patient.chest_pain_symptom === 1 ? 1 : 0,
    address: patient.address,
    emergency_contact: patient.emergency_contact,
    emergency_phone: patient.emergency_phone,
    medical_history: patient.medical_history,
    allergies: patient.allergies,
    notes: patient.notes
  })
  showAddDialog.value = true
}

// 提交患者信息
const submitPatient = async () => {
  if (!patientFormRef.value) return

  await patientFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      const payload = buildPatientPayload()
      if (editingPatient.value) {
        // 更新患者
        await api.put(`/patients/${editingPatient.value.id}`, payload)
        ElMessage.success('患者信息已更新')
      } else {
        // 创建患者
        await api.post('/patients', payload)
        ElMessage.success('患者已添加')
      }

      showAddDialog.value = false
      resetForm()
      loadPatients()
    } catch (error) {
      ElMessage.error('操作失败: ' + formatSubmitError(error))
    } finally {
      submitting.value = false
    }
  })
}

// 删除患者
const deletePatient = async (patient) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除患者 ${patient.name} 吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await api.delete(`/patients/${patient.id}`)
    ElMessage.success('患者已删除')
    loadPatients()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

// 重置表单
const resetForm = () => {
  editingPatient.value = null
  Object.assign(patientForm, {
    name: '',
    gender: 'male',
    age: null,
    birth_date: '',
    phone: '',
    occupation: '',
    height_cm: null,
    weight_kg: null,
    blood_pressure_systolic: null,
    blood_pressure_diastolic: null,
    resting_heart_rate: null,
    hrv_mean_rr: null,
    hrv_sdnn: null,
    hrv_rmssd: null,
    hrv_pnn50: null,
    hrv_lf_hf_ratio: null,
    waist_cm: null,
    total_cholesterol: null,
    ldl_cholesterol: null,
    hdl_cholesterol: null,
    triglyceride: null,
    fasting_glucose: null,
    hba1c: null,
    smoke_status: 'never',
    physical_activity: 'unknown',
    diabetes: 0,
    hypertension_dx: 0,
    dyslipidemia: 0,
    family_history_cad: 0,
    chest_pain_symptom: 0,
    address: '',
    emergency_contact: '',
    emergency_phone: '',
    medical_history: '',
    allergies: '',
    notes: ''
  })
  patientFormRef.value?.resetFields()
}

// 权限检查
const canEdit = (patient) => {
  if (userRole.value === 'admin') return true
  if (userRole.value === 'doctor') {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    return patient.doctor_id === user.id
  }
  return false
}

const canDelete = (patient) => {
  return canEdit(patient)
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadPatients()
})
</script>

<style scoped>
.patient-risk-switches {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  align-items: center;
}

.patient-list {
  padding-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}

.phone-toggle {
  margin-left: 6px;
}
</style>
