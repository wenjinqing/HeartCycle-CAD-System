<template>
  <div class="multimodal-container hc-page-shell">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <span>多模态融合模型训练</span>
          <el-tag type="warning" size="large">HRV + STFT（可选 CWT）+ 交互融合</el-tag>
        </div>
      </template>

      <el-alert
        title="多模态融合说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <p><strong>数据来源：</strong>同一批 H5 文件</p>
        <p><strong>模态1：</strong>HRV 时域/频域/非线性特征 → MLP</p>
        <p><strong>模态2：</strong>ECG → STFT 频谱图（可选再叠加 CWT 尺度图为双通道）→ 2D-CNN</p>
        <p><strong>融合：</strong>默认交互式（HRV 与 CNN 向量 Hadamard + 拼接）；可切换为简单拼接</p>
      </el-alert>

      <el-alert
        title="如何提高测试准确率 / AUC（与验证曲线的关系）"
        type="warning"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <ul class="mm-tip-list">
          <li><strong>标签与样本量：</strong>务必选择含真实标签的 <code>*_SubjectMetadata.csv</code>（或自定义标签 CSV），避免「演示标签」。总 H5 尽量 ≥50，且两类比例不要极端（可配合「类别均衡」开关）。</li>
          <li><strong>验证好但测试差：</strong>多为小样本下随机划分波动；可多次训练对比，或适当减小 <code>test_size</code> / <code>val_size</code> 让训练集更大（在 <code>multimodal_service</code> 默认参数可调时于 API 扩展）。</li>
          <li><strong>训练更充分：</strong>在不过拟合前提下增加 <code>epochs</code>（观察 val_auc 是否仍上升）；可略调低 <code>learning_rate</code> 或调整 <code>batch_size</code>。</li>
          <li><strong>模型结构：</strong>可尝试「交互式融合」与「简单拼接」对比；双通道（STFT+CWT）通常信息量更大，但需更多数据支撑。</li>
          <li><strong>指标解读：</strong>详情页顶部为<strong>测试集</strong>指标；Keras 摘要里为<strong>验证集</strong> AUC，二者不必一致，以小样本下测试波动为常态。</li>
        </ul>
      </el-alert>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="140px"
        label-position="left"
      >
        <el-form-item label="H5文件" prop="h5_files">
          <div style="display: flex; gap: 10px; width: 100%; align-items: flex-start">
            <el-select
              v-model="form.h5_files"
              multiple
              filterable
              placeholder="请选择H5文件"
              style="flex: 1"
            >
              <el-option
                v-for="file in h5Files"
                :key="file"
                :label="basename(file)"
                :value="file"
                :title="file"
              />
            </el-select>
            <el-button :loading="loadingFiles" @click="loadH5Files">刷新列表</el-button>
          </div>
          <el-empty
            v-if="!h5Files.length && !loadingFiles"
            description="暂无 H5：请先在「数据监控」上传，或检查后端数据目录"
            :image-size="72"
            style="margin-top: 8px"
          />
          <div v-else class="form-tip">
            已选择 {{ form.h5_files.length }} 个文件（每个文件 = 一个受试者）
          </div>
        </el-form-item>

        <el-form-item label="标签文件（可选）" prop="label_file">
          <el-select
            v-model="form.label_file"
            clearable
            filterable
            placeholder="不提供时自动生成演示标签"
            style="width: 100%"
          >
            <el-option
              v-for="file in csvFiles"
              :key="file"
              :label="basename(file)"
              :value="file"
              :title="file"
            />
          </el-select>
          <div class="form-tip">
            需含「路径 + 标签」列（如 file_path、label）；HeartCycle 请用
            <strong>*_SubjectMetadata.csv</strong>（File_Name、Disease_Status），不要用 FileMetadata.csv
          </div>
        </el-form-item>

        <el-divider>训练参数</el-divider>

        <el-form-item label="ECG 图像模式" prop="image_mode">
          <el-radio-group v-model="form.image_mode">
            <el-radio-button value="dual">双通道（STFT + CWT，推荐）</el-radio-button>
            <el-radio-button value="stft_only">单通道（仅 STFT，与旧模型一致）</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="融合方式" prop="fusion_mode">
          <el-radio-group v-model="form.fusion_mode">
            <el-radio-button value="interactive">交互式融合</el-radio-button>
            <el-radio-button value="concat">简单拼接（原版）</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="类别均衡" prop="use_class_weights">
          <el-switch v-model="form.use_class_weights" active-text="启用 balanced 权重" />
          <span class="form-tip">阳性/阴性样本数差异大时建议开启</span>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="训练轮数" prop="epochs">
              <el-input-number
                v-model="form.epochs"
                :min="5"
                :max="200"
                :step="5"
                style="width: 100%"
              />
              <span class="form-tip">Epochs，建议 30-50</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="批次大小" prop="batch_size">
              <el-input-number
                v-model="form.batch_size"
                :min="4"
                :max="128"
                :step="4"
                style="width: 100%"
              />
              <span class="form-tip">Batch Size，建议 16</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="学习率" prop="learning_rate">
              <el-input-number
                v-model="form.learning_rate"
                :min="0.0001"
                :max="0.01"
                :step="0.0001"
                :precision="4"
                style="width: 100%"
              />
              <span class="form-tip">Learning Rate，建议 0.001</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="ECG采样率 (Hz)" prop="fs">
              <el-input-number
                v-model="form.fs"
                :min="100"
                :max="2000"
                :step="100"
                style="width: 100%"
              />
              <span class="form-tip">默认 500 Hz</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="随机种子" prop="random_state">
              <el-input-number
                v-model="form.random_state"
                :min="0"
                :max="2147483647"
                :step="1"
                controls-position="right"
                style="width: 100%"
              />
              <span class="form-tip">划分与训练可复现</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="消融每配置轮数" prop="ablation_epochs">
              <el-input-number
                v-model="form.ablation_epochs"
                :min="5"
                :max="120"
                :step="5"
                style="width: 100%"
              />
              <span class="form-tip">与上方「训练轮数」独立，避免消融过久</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="测试集比例" prop="test_size">
              <el-slider
                v-model="form.test_size"
                :min="0.1"
                :max="0.4"
                :step="0.05"
                :format-tooltip="(val) => `${(val * 100).toFixed(0)}%`"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="验证集比例" prop="val_size">
              <el-slider
                v-model="form.val_size"
                :min="0.1"
                :max="0.3"
                :step="0.05"
                :format-tooltip="(val) => `${(val * 100).toFixed(0)}%`"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="消融选项">
          <el-switch
            v-model="form.ablation_persist"
            active-text="结果写入 MODELS_DIR（JSON）"
            style="margin-right: 16px"
          />
          <el-switch
            v-model="form.ablation_include_sw"
            active-text="含 sample_weight 对照行"
            style="margin-right: 16px"
          />
          <span class="form-tip" style="margin-right: 8px">划分种子</span>
          <el-input-number
            v-model="form.ablation_random_state"
            :min="0"
            :max="2147483647"
            :step="1"
            controls-position="right"
            style="width: 140px"
          />
          <div class="form-tip" style="display: block; margin-top: 8px; margin-left: 0">
            一键消融会串行训练多种结构，耗时远长于单次训练；划分与上方测试/验证比例一致。
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleTrain" :loading="training" size="large">
            开始训练
          </el-button>
          <el-button
            type="success"
            plain
            @click="handleAblation"
            :loading="ablationLoading"
            :disabled="training"
            size="large"
          >
            一键消融
          </el-button>
          <el-button @click="resetForm" size="large">重置</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <h3>已训练的多模态融合模型</h3>
      <el-table :data="models" v-loading="loadingModels" stripe>
        <el-table-column prop="model_id" label="模型ID" width="220" />
        <el-table-column prop="test_accuracy" label="准确率" width="100">
          <template #default="{ row }">
            {{ (row.test_accuracy * 100).toFixed(2) }}%
          </template>
        </el-table-column>
        <el-table-column prop="test_auc" label="AUC" width="100">
          <template #default="{ row }">
            {{ row.test_auc.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="n_samples" label="样本数" width="100" />
        <el-table-column prop="n_hrv_features" label="HRV特征数" width="120" />
        <el-table-column prop="image_mode" label="图像" width="100" show-overflow-tooltip />
        <el-table-column prop="fusion_mode" label="融合" width="110" show-overflow-tooltip />
        <el-table-column prop="label_source" label="标签来源" width="120" show-overflow-tooltip />
        <el-table-column label="最佳 val AUC" width="118">
          <template #default="{ row }">
            {{ row.best_val_auc != null ? row.best_val_auc.toFixed(4) : '—' }}
          </template>
        </el-table-column>
        <el-table-column label="epoch" width="100">
          <template #default="{ row }">
            <span v-if="row.epochs_trained != null">{{ row.epochs_trained }}</span>
            <span v-else>—</span>
            <span class="form-tip" style="margin-left: 2px">/ {{ row.epochs ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewModelDetail(row)">
              查看详情
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 消融结果 -->
    <el-dialog
      v-model="ablationDialogVisible"
      title="消融实验结果"
      width="920px"
      destroy-on-close
    >
      <template v-if="ablationResult">
        <el-descriptions :column="3" border size="small" class="ablation-meta">
          <el-descriptions-item label="随机种子">
            {{ ablationResult.split?.random_state }}
          </el-descriptions-item>
          <el-descriptions-item label="train / val / test">
            {{ ablationResult.split?.n_train }} /
            {{ ablationResult.split?.n_val }} /
            {{ ablationResult.split?.n_test }}
          </el-descriptions-item>
          <el-descriptions-item label="每配置 epochs">
            {{ ablationResult.epochs }}
          </el-descriptions-item>
        </el-descriptions>
        <el-table
          :data="ablationResult.rows"
          stripe
          max-height="420"
          style="width: 100%; margin-top: 16px"
        >
          <el-table-column prop="description_zh" label="配置" min-width="200" show-overflow-tooltip />
          <el-table-column label="验证 AUC" width="100">
            <template #default="{ row }">
              {{ formatMetric(row.val_auc) }}
            </template>
          </el-table-column>
          <el-table-column label="验证 F1" width="90">
            <template #default="{ row }">
              {{ formatMetric(row.val_f1) }}
            </template>
          </el-table-column>
          <el-table-column label="测试 AUC" width="100">
            <template #default="{ row }">
              {{ formatMetric(row.test_auc) }}
            </template>
          </el-table-column>
          <el-table-column label="测试 F1" width="90">
            <template #default="{ row }">
              {{ formatMetric(row.test_f1) }}
            </template>
          </el-table-column>
          <el-table-column label="权重" width="72">
            <template #default="{ row }">
              <el-tag :type="row.use_sample_weight ? 'success' : 'info'" size="small">
                {{ row.use_sample_weight ? 'SW' : '无' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="seconds" label="耗时(s)" width="88" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-text v-if="row.error" type="danger" truncated>{{ row.error }}</el-text>
              <el-text v-else type="success">完成</el-text>
            </template>
          </el-table-column>
        </el-table>
        <el-input
          :model-value="ablationResult.markdown_table || ''"
          type="textarea"
          :rows="6"
          readonly
          placeholder="Markdown 表"
          style="margin-top: 16px; font-family: monospace; font-size: 12px"
        />
      </template>
      <template #footer>
        <el-button @click="copyAblationMarkdown" :disabled="!ablationResult?.markdown_table">
          复制 Markdown 表
        </el-button>
        <el-button type="primary" @click="ablationDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 训练结果对话框 -->
    <el-dialog v-model="resultDialogVisible" title="训练完成" width="920px" top="5vh">
      <el-result icon="success" title="多模态融合模型训练成功">
        <template #sub-title>
          <p>模型ID: {{ trainingResult?.model_id }}</p>
          <p>测试集准确率: {{ (trainingResult?.test_accuracy * 100).toFixed(2) }}%</p>
          <p>测试集AUC: {{ trainingResult?.test_auc?.toFixed(4) }}</p>
        </template>
        <template #extra>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="样本数">
              {{ trainingResult?.n_samples }}
            </el-descriptions-item>
            <el-descriptions-item label="标签来源">
              {{ labelSourceLabel(trainingMeta?.label_source) }}
            </el-descriptions-item>
            <el-descriptions-item label="ECG 图像">
              {{ trainingMeta?.image_mode }}（{{ trainingMeta?.img_channels }} 通道）
            </el-descriptions-item>
            <el-descriptions-item label="融合方式">
              {{ trainingMeta?.fusion_mode }}
            </el-descriptions-item>
            <el-descriptions-item label="随机种子">
              {{ trainingMeta?.random_state ?? '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="实际 / 设定 epoch">
              {{ trainingMeta?.epochs_trained ?? '—' }} / {{ trainingMeta?.epochs ?? '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="最佳验证 AUC">
              {{ trainingMeta?.best_val_auc != null ? trainingMeta.best_val_auc.toFixed(4) : '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="混淆矩阵" :span="2">
              {{ JSON.stringify(trainingResult?.confusion_matrix) }}
            </el-descriptions-item>
          </el-descriptions>
          <KerasHistoryCharts
            v-if="trainingResult?.history && Object.keys(trainingResult.history).length"
            :history="trainingResult.history"
            height="200px"
            class="train-mm-charts"
          />
          <div style="margin-top: 20px">
            <el-button type="primary" @click="viewModelDetail(trainingResult)">
              查看详情
            </el-button>
            <el-button @click="resultDialogVisible = false">关闭</el-button>
          </div>
        </template>
      </el-result>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiService } from '@/services/api'
import KerasHistoryCharts from '@/components/charts/KerasHistoryCharts.vue'

const router = useRouter()

const formRef = ref(null)
const training = ref(false)
const loadingModels = ref(false)
const loadingFiles = ref(false)
const h5Files = ref([])
const csvFiles = ref([])
const models = ref([])
const resultDialogVisible = ref(false)
const trainingResult = ref(null)
const ablationLoading = ref(false)
const ablationDialogVisible = ref(false)
const ablationResult = ref(null)

const form = reactive({
  h5_files: [],
  label_file: null,
  epochs: 30,
  batch_size: 16,
  learning_rate: 0.001,
  test_size: 0.2,
  val_size: 0.2,
  fs: 500.0,
  image_mode: 'dual',
  fusion_mode: 'interactive',
  use_class_weights: true,
  ablation_persist: false,
  ablation_include_sw: true,
  ablation_random_state: 42,
  random_state: 42,
  ablation_epochs: 25
})

const rules = {
  h5_files: [
    { required: true, message: '请选择H5文件', trigger: 'change' },
    { type: 'array', min: 4, message: '至少选择4个文件', trigger: 'change' }
  ]
}

const trainingMeta = computed(() => trainingResult.value?.metadata ?? {})

/** 下拉展示短名，value 仍为完整路径；悬停可看 :title */
function basename(p) {
  if (p == null || typeof p !== 'string') return ''
  const i = Math.max(p.lastIndexOf('/'), p.lastIndexOf('\\'))
  return i >= 0 ? p.slice(i + 1) : p
}

const labelSourceLabel = (s) => {
  const map = {
    csv: 'CSV 标签',
    demo_random: '演示随机标签',
    demo_fallback_single_class: '标签无效（全一类）→演示标签'
  }
  return map[s] || s || '—'
}

const loadH5Files = async () => {
  loadingFiles.value = true
  try {
    const response = await apiService.getFiles()
    if (response.success) {
      const files = response.files || []
      h5Files.value = files
        .filter(file => file.filename.endsWith('.h5'))
        .map(file => file.path)
      csvFiles.value = files
        .filter(file => file.filename.endsWith('.csv'))
        .map(file => file.path)
    }
  } catch (error) {
    ElMessage.error('获取文件列表失败')
  } finally {
    loadingFiles.value = false
  }
}

const loadModels = async () => {
  loadingModels.value = true
  try {
    const response = await apiService.getMultiModalModels()
    if (response.success) {
      models.value = response.data
    }
  } catch (error) {
    ElMessage.error('获取模型列表失败')
  } finally {
    loadingModels.value = false
  }
}

const formatMetric = (v) => {
  if (v == null || Number.isNaN(v)) return '—'
  return typeof v === 'number' ? v.toFixed(4) : String(v)
}

const copyAblationMarkdown = async () => {
  const text = ablationResult.value?.markdown_table
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制 Markdown 表')
  } catch {
    ElMessage.error('复制失败，请手动全选文本框复制')
  }
}

const handleAblation = async () => {
  if (!form.h5_files?.length) {
    ElMessage.warning('请先选择 H5 文件')
    return
  }
  if (form.h5_files.length < 6) {
    ElMessage.warning('消融实验至少需要 6 个 H5 文件（分层划分），请多选文件')
    return
  }
  try {
    await ElMessageBox.confirm(
      '将按默认配置依次训练多种模型（仅 HRV、仅 CNN、多模态组合及 sample_weight 对照等），总耗时可能达数十分钟或更长。是否继续？',
      '一键消融',
      { type: 'warning', confirmButtonText: '开始', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  ablationLoading.value = true
  try {
    const payload = {
      h5_files: form.h5_files,
      label_file: form.label_file || undefined,
      random_state: form.ablation_random_state,
      test_size: form.test_size,
      val_size: form.val_size,
      fs: form.fs,
      epochs: form.ablation_epochs,
      batch_size: form.batch_size,
      learning_rate: form.learning_rate,
      include_sample_weight_ablation: form.ablation_include_sw,
      persist: form.ablation_persist
    }
    const response = await apiService.runMultiModalAblation(payload)
    if (response.success) {
      ablationResult.value = response.data
      ablationDialogVisible.value = true
      const path = response.data?.saved_path
      ElMessage.success(path ? `消融完成，已保存 ${path}` : '消融完成')
    } else {
      ElMessage.error(response.message || '消融失败')
    }
  } catch (error) {
    const d = error.response?.data?.detail
    ElMessage.error(typeof d === 'string' ? d : d?.[0]?.msg || '消融失败')
  } finally {
    ablationLoading.value = false
  }
}

const handleTrain = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    training.value = true
    try {
      const trainPayload = {
        h5_files: form.h5_files,
        label_file: form.label_file || undefined,
        epochs: form.epochs,
        batch_size: form.batch_size,
        learning_rate: form.learning_rate,
        test_size: form.test_size,
        val_size: form.val_size,
        fs: form.fs,
        image_mode: form.image_mode,
        fusion_mode: form.fusion_mode,
        use_class_weights: form.use_class_weights,
        random_state: form.random_state
      }
      const response = await apiService.trainMultiModalModel(trainPayload)

      if (response.success) {
        ElMessage.success('多模态融合模型训练成功')
        trainingResult.value = response.data
        resultDialogVisible.value = true
        loadModels()
      } else {
        ElMessage.error(response.message || '训练失败')
      }
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '训练失败')
    } finally {
      training.value = false
    }
  })
}

const handleDelete = async (model) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型 "${model.model_id}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await apiService.deleteMultiModalModel(model.model_id)
    if (response.success) {
      ElMessage.success('模型已删除')
      loadModels()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const viewModelDetail = (model) => {
  router.push(`/models/${model.model_id}`)
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

onMounted(() => {
  loadH5Files()
  loadModels()
})
</script>

<style scoped>
.multimodal-container {
  padding-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

h3 {
  margin-bottom: 20px;
  color: #303133;
}

.ablation-meta {
  margin-bottom: 0;
}

.train-mm-charts {
  margin-top: 16px;
  max-height: 720px;
  overflow-y: auto;
}

.mm-tip-list {
  margin: 0;
  padding-left: 1.25em;
  line-height: 1.65;
  font-size: 13px;
}

.mm-tip-list li {
  margin-bottom: 6px;
}
</style>
