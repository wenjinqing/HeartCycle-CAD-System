<template>
  <div class="monitor hc-page-shell">
    <el-card class="hc-card-elevated monitor-hero-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon><MonitorIcon /></el-icon>
          <span>冠心病监测与预警分析</span>
        </div>
      </template>

      <el-alert
        v-if="recordPatientId"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
        title="关联患者预测记录"
        :description="`已尝试从患者档案填入体征、实验室与危险因素（若有）；分析结果将在已登录前提下写入该患者预测记录。`"
      />

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 体征信息输入 -->
        <el-tab-pane label="体征信息" name="info">
          <el-form
            ref="formRef"
            :model="formData"
            :rules="rules"
            label-width="160px"
            class="monitor-form"
          >
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="年龄" prop="age">
                  <el-input-number
                    v-model="formData.age"
                    :min="1"
                    :max="120"
                    placeholder="请输入年龄"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="性别" prop="gender">
                  <el-radio-group v-model="formData.gender">
                    <el-radio value="M">男</el-radio>
                    <el-radio value="F">女</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="身高 (cm)" prop="height">
                  <el-input-number
                    v-model="formData.height"
                    :min="100"
                    :max="250"
                    :precision="1"
                    placeholder="请输入身高"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="体重 (kg)" prop="weight">
                  <el-input-number
                    v-model="formData.weight"
                    :min="20"
                    :max="200"
                    :precision="1"
                    placeholder="请输入体重"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item :label="formatLabelWithAbbr('BMI')" prop="bmi">
              <template #label>
                <span>BMI（身体质量指数）</span>
                <el-tooltip effect="dark" :content="getAbbreviationTooltip('BMI')" placement="right">
                  <el-icon style="margin-left: 5px; cursor: help; color: #909399;"><InfoFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-input
                v-model="calculatedBMI"
                disabled
                style="width: 300px"
              >
                <template #append>自动计算</template>
              </el-input>
            </el-form-item>

            <el-divider>血压、心率与腰围</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="收缩压 (mmHg)" prop="blood_pressure_systolic">
                  <el-input-number
                    v-model="formData.blood_pressure_systolic"
                    :min="0"
                    :max="300"
                    placeholder="选填"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="舒张压 (mmHg)" prop="blood_pressure_diastolic">
                  <el-input-number
                    v-model="formData.blood_pressure_diastolic"
                    :min="0"
                    :max="200"
                    placeholder="选填"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="静息心率 (次/分)" prop="resting_heart_rate">
                  <el-input-number
                    v-model="formData.resting_heart_rate"
                    :min="0"
                    :max="220"
                    placeholder="选填"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="腰围 (cm)" prop="waist_cm">
                  <el-input-number
                    v-model="formData.waist_cm"
                    :min="0"
                    :max="200"
                    :precision="1"
                    placeholder="选填"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider>血脂与血糖（选填，单位 mmol/L；HbA1c 为 %）</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="总胆固醇" prop="total_cholesterol">
                  <el-input-number v-model="formData.total_cholesterol" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="LDL-C" prop="ldl_cholesterol">
                  <el-input-number v-model="formData.ldl_cholesterol" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="HDL-C" prop="hdl_cholesterol">
                  <el-input-number v-model="formData.hdl_cholesterol" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="甘油三酯" prop="triglyceride">
                  <el-input-number v-model="formData.triglyceride" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="空腹血糖" prop="fasting_glucose">
                  <el-input-number v-model="formData.fasting_glucose" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="糖化血红蛋白 HbA1c" prop="hba1c">
                  <el-input-number v-model="formData.hba1c" :min="0" :max="20" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider>生活方式与危险因素（选填）</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="吸烟" prop="smoke_status">
                  <el-select v-model="formData.smoke_status" placeholder="请选择" style="width: 100%">
                    <el-option label="从不吸烟" value="never" />
                    <el-option label="已戒烟" value="former" />
                    <el-option label="目前吸烟" value="current" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="体力活动" prop="physical_activity">
                  <el-select v-model="formData.physical_activity" placeholder="请选择" style="width: 100%">
                    <el-option label="不详" value="unknown" />
                    <el-option label="久坐少动" value="sedentary" />
                    <el-option label="轻度活动" value="light" />
                    <el-option label="中度活动" value="moderate" />
                    <el-option label="重度活动/体力劳动者" value="heavy" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="合并症与症状">
              <div class="risk-switch-row">
                <el-switch v-model="formData.diabetes" :active-value="1" :inactive-value="0" active-text="糖尿病" />
                <el-switch v-model="formData.hypertension_dx" :active-value="1" :inactive-value="0" active-text="高血压（诊断）" />
                <el-switch v-model="formData.dyslipidemia" :active-value="1" :inactive-value="0" active-text="血脂异常" />
                <el-switch v-model="formData.family_history_cad" :active-value="1" :inactive-value="0" active-text="早发冠心病家族史" />
                <el-switch v-model="formData.chest_pain_symptom" :active-value="1" :inactive-value="0" active-text="胸痛/心绞痛症状" />
              </div>
            </el-form-item>

            <el-divider>模型选择</el-divider>

            <el-form-item label="预测模式" prop="predictionMode">
              <el-radio-group v-model="predictionMode" @change="handlePredictionModeChange">
                <el-radio value="single">单个模型</el-radio>
                <el-radio value="ensemble">模型集成</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="predictionMode === 'single'" label="选择模型" prop="selectedModel">
              <el-select
                v-model="selectedModel"
                placeholder="请选择模型"
                filterable
                style="width: 100%"
                :loading="loadingModels"
                @focus="loadModelList"
              >
                <el-option
                  v-for="model in modelList"
                  :key="model.model_id"
                  :label="getModelDisplayName(model)"
                  :value="model.model_id"
                >
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <span>{{ getModelDisplayName(model) }}</span>
                    <el-tag v-if="model.model_type" size="small" :type="getModelTypeTag(model.model_type)">
                      {{ getModelTypeName(model.model_type) }}
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
              <div style="margin-top: 8px">
                <el-button
                  link
                  size="small"
                  @click="loadModelList"
                  :loading="loadingModels"
                  style="padding: 0"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新列表
                </el-button>
              </div>
            </el-form-item>

            <el-form-item v-if="predictionMode === 'ensemble'" label="选择多个模型" prop="selectedModels">
              <el-select
                v-model="selectedModels"
                placeholder="请选择多个模型（至少2个）"
                filterable
                multiple
                style="width: 100%"
                :loading="loadingModels"
                @focus="loadModelList"
              >
                <el-option
                  v-for="model in modelList"
                  :key="model.model_id"
                  :label="getModelDisplayName(model)"
                  :value="model.model_id"
                >
                  <div style="display: flex; justify-content: space-between; align-items: center">
                    <span>{{ getModelDisplayName(model) }}</span>
                    <el-tag v-if="model.model_type" size="small" :type="getModelTypeTag(model.model_type)">
                      {{ getModelTypeName(model.model_type) }}
                    </el-tag>
                  </div>
                </el-option>
              </el-select>
              <div style="margin-top: 8px; display: flex; align-items: center; gap: 10px">
                <el-tag type="info" size="small">已选择 {{ selectedModels.length }} 个模型</el-tag>
                <el-button
                  link
                  size="small"
                  @click="loadModelList"
                  :loading="loadingModels"
                  style="padding: 0"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </el-form-item>

            <el-form-item v-if="predictionMode === 'ensemble'" label="集成方法">
              <el-radio-group v-model="ensembleMethod">
                <el-radio value="voting">投票集成（平均概率）</el-radio>
                <el-radio value="weighted">加权平均</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-divider>
              <span>HRV特征（心率变异性，Heart Rate Variability）</span>
              <el-tooltip effect="dark" content="HRV特征是基于ECG信号提取的心率变异性指标，反映自主神经系统的功能状态" placement="top">
                <el-icon style="margin-left: 5px; cursor: help;"><InfoFilled /></el-icon>
              </el-tooltip>
              <span style="font-size: 12px; color: #909399; margin-left: 5px">（可选，如有ECG数据）</span>
            </el-divider>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label-width="220px">
                  <template #label>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; line-height: 1.4;">
                      <span style="font-weight: 500;">平均RR间期 (ms)</span>
                      <span style="font-size: 12px; color: #909399; margin-top: 2px;">平均RR间期</span>
                    </div>
                    <el-tooltip effect="dark" content="Mean RR Interval：ECG信号中连续两个R波之间的平均时间间隔，反映平均心率，单位：ms（毫秒），HRV时域特征" placement="right">
                      <el-icon style="margin-left: 5px; cursor: help; color: #909399;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </template>
                  <el-input-number
                    v-model="formData.mean_rr"
                    :min="0"
                    :precision="2"
                    placeholder="平均RR间期"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label-width="220px">
                  <template #label>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; line-height: 1.4;">
                      <span style="font-weight: 500;">SDNN (ms)</span>
                      <span style="font-size: 12px; color: #909399; margin-top: 2px;">正常RR间期标准差</span>
                    </div>
                    <el-tooltip effect="dark" content="Standard Deviation of Normal-to-Normal intervals：正常RR间期的标准差，反映整体心率变异性，单位：ms（毫秒），HRV时域特征" placement="right">
                      <el-icon style="margin-left: 5px; cursor: help; color: #909399;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </template>
                  <el-input-number
                    v-model="formData.sdnn"
                    :min="0"
                    :precision="2"
                    placeholder="SDNN"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label-width="220px">
                  <template #label>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; line-height: 1.4;">
                      <span style="font-weight: 500;">RMSSD (ms)</span>
                      <span style="font-size: 12px; color: #909399; margin-top: 2px;">连续RR间期差值的均方根</span>
                    </div>
                    <el-tooltip effect="dark" content="Root Mean Square of Successive Differences：连续RR间期差值的均方根，主要反映副交感神经活性，单位：ms（毫秒），HRV时域特征" placement="right">
                      <el-icon style="margin-left: 5px; cursor: help; color: #909399;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </template>
                  <el-input-number
                    v-model="formData.rmssd"
                    :min="0"
                    :precision="2"
                    placeholder="RMSSD"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label-width="220px">
                  <template #label>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; line-height: 1.4;">
                      <span style="font-weight: 500;">pNN50 (%)</span>
                      <span style="font-size: 12px; color: #909399; margin-top: 2px;">相邻RR间期差异超过50ms的百分比</span>
                    </div>
                    <el-tooltip effect="dark" content="Percentage of NN intervals differing by more than 50ms：相邻RR间期差异超过50ms的百分比，反映心率变异性，单位：%（百分比），HRV时域特征" placement="right">
                      <el-icon style="margin-left: 5px; cursor: help; color: #909399;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </template>
                  <el-input-number
                    v-model="formData.pnn50"
                    :min="0"
                    :max="100"
                    :precision="2"
                    placeholder="pNN50"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label-width="220px">
                  <template #label>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; line-height: 1.4;">
                      <span style="font-weight: 500;">LF/HF比值</span>
                      <span style="font-size: 12px; color: #909399; margin-top: 2px;">低频与高频功率比值</span>
                    </div>
                    <el-tooltip effect="dark" content="Low Frequency/High Frequency Ratio：心率变异性频域分析中的低频与高频功率比值，反映自主神经系统的平衡状态，无量纲，HRV频域特征" placement="right">
                      <el-icon style="margin-left: 5px; cursor: help; color: #909399;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </template>
                  <el-input-number
                    v-model="formData.lf_hf_ratio"
                    :min="0"
                    :precision="2"
                    placeholder="LF/HF比值"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider>ECG（心电图）文件上传（自动提取特征）</el-divider>

            <el-form-item label="上传HDF5（分层数据格式5）文件">
              <template #label>
                <span>上传HDF5（分层数据格式5）文件</span>
                <el-tooltip effect="dark" :content="getAbbreviationTooltip('HDF5')" placement="right">
                  <el-icon style="margin-left: 5px; cursor: help; color: #909399;"><InfoFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-upload
                ref="uploadRef"
                :auto-upload="false"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                :limit="1"
                accept=".h5"
                :disabled="uploading"
              >
                <el-button type="primary" :loading="uploading">
                  <el-icon><Upload /></el-icon>
                  {{ selectedFile ? '重新选择文件' : '选择HDF5文件' }}
                </el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    支持上传HDF5（分层数据格式5）格式的ECG（心电图）数据文件，上传后将自动提取HRV（心率变异性）特征
                  </div>
                </template>
              </el-upload>
              <div v-if="selectedFile" class="file-info">
                <el-tag type="info" style="margin-top: 10px">
                  <el-icon><Document /></el-icon>
                  {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
                </el-tag>
                <el-button 
                  v-if="!uploading" 
                  type="primary" 
                  size="small" 
                  style="margin-left: 10px"
                  @click="handleUploadAndExtract"
                  :loading="extracting"
                >
                  <el-icon v-if="!extracting"><Upload /></el-icon>
                  {{ extracting ? '提取中...' : '提取特征' }}
                </el-button>
              </div>
              <div v-if="extractedFeatures" class="extracted-features">
                <el-alert
                  title="特征提取成功"
                  type="success"
                  :closable="false"
                  show-icon
                  style="margin-top: 10px"
                >
                  <template #default>
                    <p>已成功提取 {{ Object.keys(extractedFeatures).length }} 个HRV（心率变异性）特征</p>
                    <el-button type="primary" size="small" @click="applyExtractedFeatures">
                      <el-icon><Check /></el-icon>
                      应用到表单
                    </el-button>
                  </template>
                </el-alert>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" size="large" @click="submitForm" :loading="analyzing">
                <el-icon v-if="!analyzing"><Search /></el-icon>
                {{ analyzing ? '分析中...' : '开始分析' }}
              </el-button>
              <el-button size="large" @click="resetForm">
                <el-icon><RefreshLeft /></el-icon>
                重置表单
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 分析结果 -->
        <el-tab-pane label="分析结果" name="result" :disabled="!hasResult">
          <div v-if="analyzing" class="analyzing">
            <el-result icon="info">
              <template #icon>
                <el-icon class="is-loading" :size="60"><Loading /></el-icon>
              </template>
              <template #title>正在分析中...</template>
              <template #sub-title>请稍候，系统正在处理您的数据</template>
            </el-result>
          </div>

          <div v-else-if="analysisResult" class="result-content">
            <!-- 风险等级 -->
            <el-card class="risk-card" :class="riskClass">
              <div class="risk-header">
                <div class="risk-icon-wrapper">
                  <el-icon :size="50" :class="riskIconClass">
                    <component :is="riskIcon" />
                  </el-icon>
                </div>
                <div class="risk-title-section">
                  <h2>风险评估结果</h2>
                  <p class="risk-level">{{ riskLevel }}</p>
                </div>
              </div>
              <div class="risk-visualization">
                <div class="risk-score-section">
                  <div class="score-label">风险评分</div>
                  <div class="score-value">{{ riskScore }}%</div>
                </div>
                <el-progress 
                  :percentage="parseFloat(riskScore)" 
                  :color="riskProgressColor"
                  :stroke-width="20"
                  striped
                  striped-flow
                  :duration="2"
                  class="risk-progress"
                />
                <div class="risk-indicator">
                  <span class="indicator-item" :class="{ active: parseFloat(riskScore) < 30 }">
                    <span class="indicator-dot low"></span>
                    <span>低风险 (0-30%)</span>
                  </span>
                  <span class="indicator-item" :class="{ active: parseFloat(riskScore) >= 30 && parseFloat(riskScore) < 60 }">
                    <span class="indicator-dot medium"></span>
                    <span>中风险 (30-60%)</span>
                  </span>
                  <span class="indicator-item" :class="{ active: parseFloat(riskScore) >= 60 }">
                    <span class="indicator-dot high"></span>
                    <span>高风险 (60-100%)</span>
                  </span>
                </div>
              </div>
              
              <!-- 概率分布可视化 -->
              <div class="probability-distribution">
                <div class="prob-item">
                  <div class="prob-label">
                    <el-icon><CircleCheck /></el-icon>
                    <span>低风险概率</span>
                  </div>
                  <div class="prob-bar-wrapper">
                    <div 
                      class="prob-bar prob-bar-low" 
                      :style="{ width: (analysisResult.probability[0] * 100) + '%' }"
                    >
                      <span class="prob-value">{{ (analysisResult.probability[0] * 100).toFixed(1) }}%</span>
                    </div>
                  </div>
                </div>
                <div class="prob-item">
                  <div class="prob-label">
                    <el-icon><Warning /></el-icon>
                    <span>高风险概率</span>
                  </div>
                  <div class="prob-bar-wrapper">
                    <div 
                      class="prob-bar prob-bar-high" 
                      :style="{ width: (analysisResult.probability[1] * 100) + '%' }"
                    >
                      <span class="prob-value">{{ (analysisResult.probability[1] * 100).toFixed(1) }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 预测详情 -->
            <el-card style="margin-top: 20px" class="prediction-details-card">
              <template #header>
                <div class="card-header-with-actions">
                  <div>
                    <span style="font-weight: 600; font-size: 18px">预测详情</span>
                    <el-tag v-if="analysisResult.method === 'ensemble'" type="info" style="margin-left: 10px">
                      集成预测（{{ analysisResult.method === 'voting' ? '投票' : '加权平均' }}）
                    </el-tag>
                  </div>
                  <div class="card-actions">
                    <el-button 
                      size="small" 
                      :icon="Document" 
                      @click="exportResults"
                      circle
                      title="导出JSON（JavaScript对象表示法）"
                    />
                    <el-button 
                      size="small" 
                      type="primary"
                      :icon="Document" 
                      @click="exportPDFReport"
                      circle
                      title="导出PDF报告"
                    />
                    <el-button 
                      size="small" 
                      :icon="Printer" 
                      @click="printResults"
                      circle
                      title="打印结果"
                    />
                  </div>
                </div>
              </template>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="预测方法">
                  {{ analysisResult.method === 'ensemble' ? '模型集成' : '单个模型' }}
                  <el-tag v-if="analysisResult.method === 'ensemble'" type="info" size="small" style="margin-left: 10px">
                    {{ analysisResult.modelCount }} 个模型
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="预测类别">
                  <el-tag :type="analysisResult.prediction === 1 ? 'danger' : 'success'">
                    {{ analysisResult.prediction === 1 ? '高风险' : '低风险' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="预测置信度">
                  {{ (analysisResult.confidence * 100).toFixed(2) }}%
                </el-descriptions-item>
                <el-descriptions-item v-if="analysisResult.agreement !== undefined" label="模型一致性">
                  {{ (analysisResult.agreement * 100).toFixed(1) }}%
                  <el-tag :type="analysisResult.agreement > 0.8 ? 'success' : (analysisResult.agreement > 0.5 ? 'warning' : 'danger')" size="small" style="margin-left: 10px">
                    {{ analysisResult.agreement > 0.8 ? '高度一致' : (analysisResult.agreement > 0.5 ? '中等一致' : '存在分歧') }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="类别0概率">
                  {{ (analysisResult.probability[0] * 100).toFixed(2) }}%
                </el-descriptions-item>
                <el-descriptions-item label="类别1概率">
                  {{ (analysisResult.probability[1] * 100).toFixed(2) }}%
                </el-descriptions-item>
                <el-descriptions-item v-if="analysisResult.individualPredictions" label="各模型预测" :span="2">
                  <div style="display: flex; gap: 8px; flex-wrap: wrap">
                    <el-tag
                      v-for="(pred, index) in analysisResult.individualPredictions"
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

            <!-- 预警信息和建议 -->
            <el-card v-if="analysisResult.prediction === 1" class="warning-card" style="margin-top: 20px">
              <template #header>
                <div style="display: flex; align-items: center; gap: 10px">
                  <el-icon :size="24" style="color: #f56c6c"><Warning /></el-icon>
                  <span style="font-weight: 600; font-size: 18px; color: #f56c6c">风险预警与健康建议</span>
                </div>
              </template>
              <div class="warning-content">
                <el-alert
                  title="检测到冠心病高风险"
                  type="warning"
                  :closable="false"
                  show-icon
                  style="margin-bottom: 20px"
                >
                  <template #default>
                    <p style="margin: 0; font-size: 15px; line-height: 1.6">
                      根据本次分析，您的冠心病风险评分为 <strong>{{ riskScore }}%</strong>，属于高风险范围。
                      请务必重视并采取相应的预防措施。
                    </p>
                  </template>
                </el-alert>
                
                <div class="recommendations">
                  <h4 style="margin: 0 0 15px 0; color: #303133; font-size: 16px">
                    <el-icon style="margin-right: 8px; color: #409eff"><CircleCheck /></el-icon>
                    建议采取以下措施：
                  </h4>
                  <el-row :gutter="20">
                    <el-col :span="12">
                      <div class="recommendation-item">
                        <div class="recommendation-icon medical">
                          <el-icon :size="28"><Document /></el-icon>
                        </div>
                        <div class="recommendation-content">
                          <h5>及时就医检查</h5>
                          <p>建议尽快前往心内科进行专业检查，包括心电图、心脏超声、血液检查等，以明确诊断。</p>
                        </div>
                      </div>
                    </el-col>
                    <el-col :span="12">
                      <div class="recommendation-item">
                        <div class="recommendation-icon diet">
                          <el-icon :size="28"><Document /></el-icon>
                        </div>
                        <div class="recommendation-content">
                          <h5>调整饮食习惯</h5>
                          <p>控制盐分和脂肪摄入，减少高胆固醇食物，增加蔬菜水果，保持均衡营养。</p>
                        </div>
                      </div>
                    </el-col>
                    <el-col :span="12">
                      <div class="recommendation-item">
                        <div class="recommendation-icon exercise">
                          <el-icon :size="28"><Document /></el-icon>
                        </div>
                        <div class="recommendation-content">
                          <h5>适量规律运动</h5>
                          <p>每周至少150分钟中等强度有氧运动，如快走、游泳、慢跑，避免剧烈运动。</p>
                        </div>
                      </div>
                    </el-col>
                    <el-col :span="12">
                      <div class="recommendation-item">
                        <div class="recommendation-icon monitor">
                          <el-icon :size="28"><Document /></el-icon>
                        </div>
                        <div class="recommendation-content">
                          <h5>定期监测复查</h5>
                          <p>建议每3-6个月进行一次心血管健康评估，持续监测相关指标变化。</p>
                        </div>
                      </div>
                    </el-col>
                  </el-row>
                </div>
              </div>
            </el-card>

            <!-- 低风险建议 -->
            <el-card v-else class="success-card" style="margin-top: 20px">
              <template #header>
                <div style="display: flex; align-items: center; gap: 10px">
                  <el-icon :size="24" style="color: #67c23a"><CircleCheck /></el-icon>
                  <span style="font-weight: 600; font-size: 18px; color: #67c23a">健康提示</span>
                </div>
              </template>
              <div class="success-content">
                <p style="margin: 0 0 15px 0; font-size: 15px; line-height: 1.6; color: #606266">
                  根据本次分析，您的冠心病风险评分为 <strong>{{ riskScore }}%</strong>，属于低风险范围。
                  继续保持健康的生活方式，定期进行健康检查。
                </p>
                <div class="health-tips">
                  <el-tag type="success" size="large" effect="plain" style="margin-right: 10px; margin-bottom: 10px">
                    ✓ 保持规律作息
                  </el-tag>
                  <el-tag type="success" size="large" effect="plain" style="margin-right: 10px; margin-bottom: 10px">
                    ✓ 均衡饮食
                  </el-tag>
                  <el-tag type="success" size="large" effect="plain" style="margin-right: 10px; margin-bottom: 10px">
                    ✓ 适度运动
                  </el-tag>
                  <el-tag type="success" size="large" effect="plain" style="margin-right: 10px; margin-bottom: 10px">
                    ✓ 定期体检
                  </el-tag>
                </div>
              </div>
            </el-card>

            <!-- SHAP（SHapley Additive exPlanations）解释分析 -->
            <div v-if="shapInstanceData || shapGlobalData" style="margin-top: 20px">
              <ShapExplanation
                :shap-data="shapInstanceData"
                :global-importance="shapGlobalData"
              />
            </div>

            <!-- H5 心电信号可视化 -->
            <div v-if="h5Signals" style="margin-top: 20px">
              <el-divider>原始心电信号</el-divider>

              <!-- ECG -->
              <el-card v-if="h5Signals.ecg" style="margin-bottom: 16px">
                <template #header>
                  <span>ECG 心电图</span>
                  <el-tag size="small" style="margin-left: 8px">单位: mV</el-tag>
                </template>
                <div ref="monitorEcgRef" style="height: 220px"></div>
              </el-card>

              <!-- ICG -->
              <el-card v-if="h5Signals.icg" style="margin-bottom: 16px">
                <template #header>
                  <span>ICG 阻抗心动图</span>
                  <el-tag size="small" style="margin-left: 8px">单位: Ω</el-tag>
                </template>
                <div ref="monitorIcgRef" style="height: 220px"></div>
              </el-card>

              <!-- dZ/dt -->
              <el-card v-if="h5Signals.icg" style="margin-bottom: 16px">
                <template #header><span>dZ/dt 信号</span></template>
                <div ref="monitorDzRef" style="height: 220px"></div>
              </el-card>

              <!-- ECHO -->
              <el-card v-if="h5Signals.echo" style="margin-bottom: 16px">
                <template #header><span>超声心动图 (ECHO)</span></template>
                <canvas ref="monitorEchoRef" style="width:100%;height:260px;display:block"></canvas>
              </el-card>
            </div>

            <!-- 调试信息 -->
            <div v-if="analysisResult && !shapInstanceData && !shapGlobalData" style="margin-top: 20px">
              <el-alert
                title="SHAP解释数据加载中或不可用"
                type="info"
                :closable="false"
                show-icon
              >
                <template #default>
                  <p>正在尝试加载SHAP解释数据，请稍候...</p>
                  <p style="font-size: 12px; color: #909399; margin-top: 5px">
                    如果长时间未显示，可能是模型训练数据文件不可用。请查看浏览器控制台了解详情。
                  </p>
                </template>
              </el-alert>
            </div>
          </div>

          <div v-else class="no-result">
            <el-empty description="暂无分析结果，请先填写信息并进行分析" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor as MonitorIcon, Search, Warning, Upload, Document, Loading, Refresh, RefreshLeft, Check, CircleCheck, InfoFilled, SuccessFilled, Printer } from '@element-plus/icons-vue'
import { apiService } from '../services/api'
import { storage } from '../utils/storage'
import { exportPDFReport as generatePDF } from '../utils/pdfReport'
import ShapExplanation from '../components/ShapExplanation.vue'
import { formatLabelWithAbbr, getAbbreviationTooltip } from '../utils/abbreviations'
import { appendExtendedClinicalFeaturesFromForm } from '../utils/clinicalFeatureVector'

export default {
  name: 'Monitor',
  components: {
    MonitorIcon,
    Search,
    Warning,
    Upload,
    Document,
    Loading,
    Refresh,
    RefreshLeft,
    Check,
    CircleCheck,
    InfoFilled,
    SuccessFilled,
    Printer,
    ShapExplanation
  },
  setup() {
    const route = useRoute()
    const recordPatientId = ref(null)

    const formRef = ref(null)
    const uploadRef = ref(null)
    const activeTab = ref('info')
    const analyzing = ref(false)
    const analysisResult = ref(null)
    const shapInstanceData = ref(null) // SHAP（SHapley Additive exPlanations）单样本解释数据
    const shapGlobalData = ref(null) // SHAP（SHapley Additive exPlanations）全局重要性数据
    const selectedFile = ref(null)
    const uploading = ref(false)
    const extracting = ref(false)
    const extractedFeatures = ref(null)
    const uploadedFilePath = ref(null)

    // H5信号可视化
    const h5Signals = ref(null)
    const monitorEcgRef = ref(null)
    const monitorIcgRef = ref(null)
    const monitorDzRef = ref(null)
    const monitorEchoRef = ref(null)
    let signalCharts = []
    const selectedModel = ref('')
    const selectedModels = ref([])
    const modelList = ref([])
    const loadingModels = ref(false)
    const predictionMode = ref('single') // 'single' 或 'ensemble'
    const ensembleMethod = ref('voting') // 'voting' 或 'weighted'

    const defaultMonitorForm = () => ({
      age: null,
      gender: 'M',
      height: null,
      weight: null,
      blood_pressure_systolic: null,
      blood_pressure_diastolic: null,
      resting_heart_rate: null,
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
      mean_rr: null,
      sdnn: null,
      rmssd: null,
      pnn50: null,
      lf_hf_ratio: null
    })

    const formData = ref(defaultMonitorForm())

    const applyPatientProfileToForm = (p) => {
      if (!p) return
      const fd = formData.value
      if (p.age != null && p.age !== '') fd.age = p.age
      const g = (p.gender != null ? String(p.gender) : '').toLowerCase()
      if (g === 'female' || g === 'f' || g === '女' || g === '2') fd.gender = 'F'
      else if (g === 'male' || g === 'm' || g === '男' || g === '1') fd.gender = 'M'
      if (p.height_cm != null) fd.height = p.height_cm
      if (p.weight_kg != null) fd.weight = p.weight_kg
      if (p.blood_pressure_systolic != null) fd.blood_pressure_systolic = p.blood_pressure_systolic
      if (p.blood_pressure_diastolic != null) fd.blood_pressure_diastolic = p.blood_pressure_diastolic
      if (p.resting_heart_rate != null) fd.resting_heart_rate = p.resting_heart_rate
      if (p.waist_cm != null) fd.waist_cm = p.waist_cm
      if (p.total_cholesterol != null) fd.total_cholesterol = p.total_cholesterol
      if (p.ldl_cholesterol != null) fd.ldl_cholesterol = p.ldl_cholesterol
      if (p.hdl_cholesterol != null) fd.hdl_cholesterol = p.hdl_cholesterol
      if (p.triglyceride != null) fd.triglyceride = p.triglyceride
      if (p.fasting_glucose != null) fd.fasting_glucose = p.fasting_glucose
      if (p.hba1c != null) fd.hba1c = p.hba1c
      if (p.smoke_status) fd.smoke_status = p.smoke_status
      if (p.physical_activity) fd.physical_activity = p.physical_activity
      if (p.diabetes === 0 || p.diabetes === 1) fd.diabetes = p.diabetes
      if (p.hypertension_dx === 0 || p.hypertension_dx === 1) fd.hypertension_dx = p.hypertension_dx
      if (p.dyslipidemia === 0 || p.dyslipidemia === 1) fd.dyslipidemia = p.dyslipidemia
      if (p.family_history_cad === 0 || p.family_history_cad === 1) fd.family_history_cad = p.family_history_cad
      if (p.chest_pain_symptom === 0 || p.chest_pain_symptom === 1) fd.chest_pain_symptom = p.chest_pain_symptom
      if (p.hrv_mean_rr != null) fd.mean_rr = p.hrv_mean_rr
      if (p.hrv_sdnn != null) fd.sdnn = p.hrv_sdnn
      if (p.hrv_rmssd != null) fd.rmssd = p.hrv_rmssd
      if (p.hrv_pnn50 != null) fd.pnn50 = p.hrv_pnn50
      if (p.hrv_lf_hf_ratio != null) fd.lf_hf_ratio = p.hrv_lf_hf_ratio
    }

    const rules = {
      age: [
        { required: true, message: '请输入年龄', trigger: 'blur' }
      ],
      gender: [
        { required: true, message: '请选择性别', trigger: 'change' }
      ],
      height: [
        { required: true, message: '请输入身高', trigger: 'blur' }
      ],
      weight: [
        { required: true, message: '请输入体重', trigger: 'blur' }
      ]
    }

    const calculatedBMI = computed(() => {
      if (formData.value.height && formData.value.weight) {
        const heightInM = formData.value.height / 100
        return (formData.value.weight / (heightInM * heightInM)).toFixed(2)
      }
      return ''
    })

    const hasResult = computed(() => {
      return analysisResult.value !== null
    })

    const riskScore = computed(() => {
      if (!analysisResult.value) return 0
      return (analysisResult.value.probability[1] * 100).toFixed(1)
    })

    const riskLevel = computed(() => {
      const score = parseFloat(riskScore.value)
      if (score < 30) return '低风险'
      if (score < 60) return '中风险'
      return '高风险'
    })

    const riskClass = computed(() => {
      const score = parseFloat(riskScore.value)
      if (score < 30) return 'risk-low'
      if (score < 60) return 'risk-medium'
      return 'risk-high'
    })

    const riskIcon = computed(() => {
      const score = parseFloat(riskScore.value)
      if (score < 30) return 'CircleCheck'
      if (score < 60) return 'InfoFilled'
      return 'Warning'
    })

    const riskIconClass = computed(() => {
      const score = parseFloat(riskScore.value)
      if (score < 30) return 'risk-icon-low'
      if (score < 60) return 'risk-icon-medium'
      return 'risk-icon-high'
    })

    const riskProgressColor = computed(() => {
      const score = parseFloat(riskScore.value)
      if (score < 30) {
        return [
          { color: '#67c23a', percentage: 30 },
          { color: '#95d475', percentage: 100 }
        ]
      } else if (score < 60) {
        return [
          { color: '#e6a23c', percentage: 60 },
          { color: '#f0a020', percentage: 100 }
        ]
      } else {
        return [
          { color: '#f56c6c', percentage: 60 },
          { color: '#ff4d4f', percentage: 100 }
        ]
      }
    })

    const handleFileChange = (file) => {
      if (file.raw) {
        selectedFile.value = file.raw
        extractedFeatures.value = null
        uploadedFilePath.value = null
      }
    }

    const handleFileRemove = () => {
      selectedFile.value = null
      extractedFeatures.value = null
      uploadedFilePath.value = null
      h5Signals.value = null
      signalCharts.forEach(c => c.dispose())
      signalCharts = []
    }

    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    const handleUploadAndExtract = async () => {
      if (!selectedFile.value) {
        ElMessage.warning('请先选择文件')
        return
      }

      try {
        uploading.value = true
        
        // 1. 上传文件
        ElMessage.info('正在上传文件...')
        const uploadResponse = await apiService.uploadFile(selectedFile.value)
        // 处理不同的响应格式
        const uploadResult = uploadResponse.data || uploadResponse
        uploadedFilePath.value = uploadResult.file_path
        
        ElMessage.success('文件上传成功，开始提取特征...')
        uploading.value = false
        extracting.value = true

        // 同步解析H5信号用于可视化（后台静默进行，不阻塞特征提取）
        try {
          const vizFormData = new FormData()
          vizFormData.append('file', selectedFile.value)
          const token = localStorage.getItem('access_token')
          const baseUrl = uploadResponse.config?.baseURL || apiService.getBaseUrl?.() || 'http://localhost:8009/api/v1'
          const vizRes = await fetch(`${baseUrl}/h5/visualize`, {
            method: 'POST',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: vizFormData
          })
          if (vizRes.ok) {
            const vizData = await vizRes.json()
            h5Signals.value = vizData.signals
            // 等待DOM更新后渲染图表
            setTimeout(renderSignalCharts, 300)
          }
        } catch (_e) {
          // 信号解析失败不影响主流程
        }

        // 2. 提取特征
        const extractResponse = await apiService.extractFeatures({
          file_path: uploadedFilePath.value,
          use_existing_rpeaks: true,
          extract_hrv: true,
          extract_clinical: false
        })

        // 处理不同的响应格式
        const extractResult = extractResponse.data || extractResponse
        const taskId = extractResult.task_id
        if (!taskId) {
          throw new Error('未获取到任务ID')
        }

        // 3. 轮询查询特征提取状态
        let statusResponse = { status: 'pending' }
        let attempts = 0
        const maxAttempts = 60 // 最多等待60秒

        while (statusResponse.status === 'pending' && attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 1000))
          const response = await apiService.getFeatureStatus(taskId)
          statusResponse = response.data || response
          attempts++
          
          if (statusResponse.status === 'processing') {
            ElMessage.info('特征提取中，请稍候...')
          }
        }
        
        const status = statusResponse

        extracting.value = false

        if (status.status === 'completed' && status.result) {
          extractedFeatures.value = status.result
          ElMessage.success('特征提取成功！')
          
          // 自动应用到表单
          applyExtractedFeatures()
        } else if (status.status === 'failed') {
          throw new Error(status.error || '特征提取失败')
        } else {
          throw new Error('特征提取超时')
        }
      } catch (error) {
        uploading.value = false
        extracting.value = false
        ElMessage.error(`操作失败: ${error.message}`)
        console.error('Upload and extract error:', error)
      }
    }

    const applyExtractedFeatures = () => {
      if (!extractedFeatures.value) return

      const features = extractedFeatures.value
      
      // 将提取的特征应用到表单
      if (features.mean_rr !== undefined) formData.value.mean_rr = features.mean_rr
      if (features.sdnn !== undefined) formData.value.sdnn = features.sdnn
      if (features.rmssd !== undefined) formData.value.rmssd = features.rmssd
      if (features.pnn50 !== undefined) formData.value.pnn50 = features.pnn50
      if (features.lf_hf_ratio !== undefined) formData.value.lf_hf_ratio = features.lf_hf_ratio
      
      ElMessage.success('特征已应用到表单')
    }

    const exportResults = () => {
      if (!analysisResult.value) return
      
      const data = {
        评估时间: new Date().toLocaleString('zh-CN'),
        风险等级: riskLevel.value,
        风险评分: `${riskScore.value}%`,
        预测类别: analysisResult.value.prediction === 1 ? '高风险' : '低风险',
        预测置信度: `${(analysisResult.value.confidence * 100).toFixed(2)}%`,
        低风险概率: `${(analysisResult.value.probability[0] * 100).toFixed(2)}%`,
        高风险概率: `${(analysisResult.value.probability[1] * 100).toFixed(2)}%`,
        预测方法: analysisResult.value.method === 'ensemble' ? '模型集成' : '单个模型',
        模型数量: analysisResult.value.modelCount || 1,
      }
      
      if (analysisResult.value.agreement !== undefined) {
        data['模型一致性'] = `${(analysisResult.value.agreement * 100).toFixed(1)}%`
      }
      
      // 导出为JSON
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `风险评估结果_${new Date().getTime()}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
        ElMessage.success('JSON（JavaScript对象表示法）结果已导出')
    }

    const exportPDFReport = async () => {
      if (!analysisResult.value) {
        ElMessage.warning('暂无分析结果')
        return
      }

      try {
        const loadingMessage = ElMessage({
          message: '正在生成PDF报告...',
          type: 'info',
          duration: 0
        })

        // 准备报告数据
        const reportData = {
          riskLevel: riskLevel.value,
          riskScore: riskScore.value,
          prediction: analysisResult.value.prediction,
          confidence: analysisResult.value.confidence,
          probability: analysisResult.value.probability,
          method: analysisResult.value.method,
          modelCount: analysisResult.value.modelCount,
          formData: {
            ...formData.value,
            bmi: calculatedBMI.value ? parseFloat(calculatedBMI.value) : null
          }
        }

        // 获取结果区域的元素
        const resultElement = document.querySelector('.result-content')
        
        await generatePDF({
          element: resultElement,
          data: reportData,
          filename: `风险评估报告_${new Date().getTime()}.pdf`,
          onProgress: (progress, message) => {
            loadingMessage.message = message || `正在生成PDF报告... ${progress}%`
          }
        })

        loadingMessage.close()
        ElMessage.success('PDF报告已生成并下载')
      } catch (error) {
        console.error('PDF导出失败:', error)
        ElMessage.error('PDF报告生成失败: ' + (error.message || '未知错误'))
      }
    }

    const printResults = () => {
      window.print()
    }

    const resetForm = () => {
      formData.value = defaultMonitorForm()
      formRef.value?.clearValidate?.()
      analysisResult.value = null
      shapInstanceData.value = null
      shapGlobalData.value = null
      selectedFile.value = null
      extractedFeatures.value = null
      uploadedFilePath.value = null
      uploading.value = false
      extracting.value = false
      uploadRef.value?.clearFiles()
      selectedModel.value = ''
      selectedModels.value = []
      predictionMode.value = 'single'
    }

    const handlePredictionModeChange = (mode) => {
      if (mode === 'single') {
        selectedModels.value = []
      } else {
        selectedModel.value = ''
      }
    }

    const loadModelList = async () => {
      try {
        loadingModels.value = true
        const modelsResponse = await apiService.getModels()
        
        // 处理不同的响应格式
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
        
        // 按创建时间排序（最新的在前）
        models.sort((a, b) => {
          const timeA = new Date(a.created_at || 0).getTime()
          const timeB = new Date(b.created_at || 0).getTime()
          return timeB - timeA
        })
        
        modelList.value = models
        
        // 如果没有选择模型且列表不为空，自动选择第一个
        if (!selectedModel.value && models.length > 0) {
          selectedModel.value = models[0].model_id
        }
      } catch (error) {
        console.error('加载模型列表失败:', error)
        ElMessage.error(`加载模型列表失败: ${error.message}`)
        modelList.value = []
      } finally {
        loadingModels.value = false
      }
    }

    const getModelDisplayName = (model) => {
      // 生成模型的显示名称
      let name = model.model_id || '未知模型'
      
      // 如果有创建时间，格式化显示
      if (model.created_at) {
        try {
          const date = new Date(model.created_at)
          const timeStr = date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          })
          name = `${name} (${timeStr})`
        } catch (e) {
          // 忽略日期解析错误
        }
      }
      
      // 如果有模型类型，添加到名称中
      if (model.model_type) {
        const typeName = getModelTypeName(model.model_type)
        name = `${name} - ${typeName}`
      }
      
      return name
    }

    const getModelTypeName = (type) => {
      const names = {
        'lr': '逻辑回归',
        'svm': '支持向量机',
        'rf': '随机森林'
      }
      return names[type] || type
    }

    const getModelTypeTag = (type) => {
      const tags = {
        'lr': 'primary',
        'svm': 'success',
        'rf': 'warning'
      }
      return tags[type] || 'info'
    }

    const lastRoutePatientId = ref(null)

    const patientIdFromRouteQuery = () => {
      const raw = route.query.patient_id
      const q = Array.isArray(raw) ? raw[0] : raw
      if (q === undefined || q === null || String(q).trim() === '') return null
      const n = parseInt(String(q), 10)
      if (Number.isNaN(n) || n <= 0) return null
      return n
    }

    const hydratePatientFromRoute = async () => {
      const n = patientIdFromRouteQuery()
      if (!n) {
        recordPatientId.value = null
        lastRoutePatientId.value = null
        return
      }
      const switchedPatient = lastRoutePatientId.value !== n
      lastRoutePatientId.value = n
      recordPatientId.value = n
      if (switchedPatient) {
        formData.value = defaultMonitorForm()
      }
      try {
        const res = await apiService.getPatient(n)
        if (res?.success && res.data) {
          applyPatientProfileToForm(res.data)
          if (switchedPatient) {
            ElMessage.success('已从患者档案填入体征、实验室与危险因素，可继续修改后再分析')
          }
        }
      } catch {
        ElMessage.warning('加载患者档案失败，请手动填写体征信息')
      }
    }

    // 路由仅 query 变化时组件会复用，onMounted 不会再次执行，必须 watch patient_id
    watch(
      () => route.query.patient_id,
      () => {
        hydratePatientFromRoute()
      },
      { immediate: true }
    )

    onMounted(() => {
      loadModelList()
    })

    const handleTabChange = (tabName) => {
      if (tabName === 'result' && !hasResult.value) {
        ElMessage.warning('请先完成分析')
        activeTab.value = 'info'
      }
    }

    const buildFeatureVector = () => {
      // 如果已经提取了完整的特征，优先使用提取的特征
      if (extractedFeatures.value) {
        return buildFeatureVectorFromExtracted(extractedFeatures.value)
      }
      
      // 否则使用表单数据构建基础特征向量（10 个核心 + 末尾扩展临床维，与 clinicalFeatureVector.js 一致）
      const features = []
      
      // 临床特征（5个）
      features.push(formData.value.age || 0)
      features.push(formData.value.gender === 'M' ? 1 : 0)
      features.push(formData.value.height || 0)
      features.push(formData.value.weight || 0)
      features.push(parseFloat(calculatedBMI.value) || 0)
      
      // HRV基础特征（5个）
      features.push(formData.value.mean_rr || 0)
      features.push(formData.value.sdnn || 0)
      features.push(formData.value.rmssd || 0)
      features.push(formData.value.pnn50 || 0)
      features.push(formData.value.lf_hf_ratio || 0)

      appendExtendedClinicalFeaturesFromForm(features, formData.value)

      return features
    }

    const buildFeatureVectorFromExtracted = (extracted) => {
      // 从提取的特征字典构建特征向量
      // 特征顺序需要与训练时的特征顺序一致
      const features = []
      
      // 临床特征（5个）
      features.push(extracted.age || extracted.height_cm || formData.value.age || 0)
      features.push(extracted.gender_male !== undefined ? extracted.gender_male : (formData.value.gender === 'M' ? 1 : 0))
      features.push(extracted.height_cm || formData.value.height || 0)
      features.push(extracted.weight_kg || formData.value.weight || 0)
      features.push(extracted.bmi || parseFloat(calculatedBMI.value) || 0)
      
      // HRV时域特征（优先使用提取的，否则使用表单值）
      features.push(extracted.mean_rr || formData.value.mean_rr || 0)
      features.push(extracted.sdnn || extracted.std_rr || formData.value.sdnn || 0)
      features.push(extracted.rmssd || formData.value.rmssd || 0)
      features.push(extracted.pnn50 || formData.value.pnn50 || 0)
      
      // HRV频域特征
      features.push(extracted.lf_hf_ratio || formData.value.lf_hf_ratio || 0)
      
      // 如果有更多特征，添加进去（保持向后兼容）
      // 时域特征
      if (extracted.min_rr !== undefined) features.push(extracted.min_rr)
      if (extracted.max_rr !== undefined) features.push(extracted.max_rr)
      if (extracted.median_rr !== undefined) features.push(extracted.median_rr)
      if (extracted.sdsd !== undefined) features.push(extracted.sdsd)
      if (extracted.mean_hr !== undefined) features.push(extracted.mean_hr)
      
      // 频域特征
      if (extracted.total_power !== undefined) features.push(extracted.total_power)
      if (extracted.vlf_power !== undefined) features.push(extracted.vlf_power)
      if (extracted.lf_power !== undefined) features.push(extracted.lf_power)
      if (extracted.hf_power !== undefined) features.push(extracted.hf_power)
      
      // 非线性特征
      if (extracted.sd1 !== undefined) features.push(extracted.sd1)
      if (extracted.sd2 !== undefined) features.push(extracted.sd2)
      if (extracted.sd1_sd2_ratio !== undefined) features.push(extracted.sd1_sd2_ratio)
      if (extracted.sample_entropy !== undefined) features.push(extracted.sample_entropy)
      if (extracted.approximate_entropy !== undefined) features.push(extracted.approximate_entropy)

      appendExtendedClinicalFeaturesFromForm(features, formData.value)

      return features
    }

    const submitForm = async () => {
      if (!formRef.value) return
      
      try {
        await formRef.value.validate()
        
        analyzing.value = true
        activeTab.value = 'result'
        // 如果已有信号数据，延时渲染图表（等待tab切换完成）
        if (h5Signals.value) setTimeout(renderSignalCharts, 400)
        
        // 如果上传了文件但还没有提取特征，先提取
        if (selectedFile.value && !extractedFeatures.value) {
          ElMessage.info('正在提取特征...')
          await handleUploadAndExtract()
          if (!extractedFeatures.value) {
            throw new Error('特征提取失败，无法继续预测')
          }
          ElMessage.success('特征提取完成')
        }
        
        // 构建特征向量
        const features = buildFeatureVector()
        
        // 根据预测模式选择使用单个模型还是集成模型
        let predictionResponse
        
        if (predictionMode.value === 'ensemble') {
          // 集成预测
          if (!selectedModels.value || selectedModels.value.length < 2) {
            throw new Error('集成预测需要选择至少2个模型')
          }
          
          predictionResponse = await apiService.predictEnsemble({
            model_ids: selectedModels.value,
            features: features,
            method: ensembleMethod.value,
            ...(recordPatientId.value ? { patient_id: recordPatientId.value } : {})
          })
        } else {
          // 单个模型预测
          let modelId = selectedModel.value
          if (!modelId) {
            // 如果没有选择模型，尝试获取模型列表并选择第一个
            const modelsResponse = await apiService.getModels()
            
            // 处理不同的响应格式
            let availableModels = []
            if (modelsResponse.data && modelsResponse.data.models) {
              availableModels = modelsResponse.data.models
            } else if (modelsResponse.models) {
              availableModels = modelsResponse.models
            } else if (Array.isArray(modelsResponse)) {
              availableModels = modelsResponse
            } else if (modelsResponse.data && Array.isArray(modelsResponse.data)) {
              availableModels = modelsResponse.data
            }
            
            if (!availableModels || availableModels.length === 0) {
              throw new Error('没有可用的模型，请先训练模型。可以在"模型训练"页面训练模型。')
            }
            
            modelId = availableModels[0].model_id
            selectedModel.value = modelId // 自动选择第一个模型
          }
          
          // 进行预测
          predictionResponse = await apiService.predict({
            model_id: modelId,
            features: features,
            ...(recordPatientId.value ? { patient_id: recordPatientId.value } : {})
          })
        }
        
        // 处理不同的响应格式
        let prediction = predictionResponse
        if (predictionResponse.data) {
          prediction = predictionResponse.data
        } else if (predictionResponse.prediction !== undefined) {
          prediction = predictionResponse
        }
        
        analysisResult.value = {
          prediction: prediction.prediction,
          probability: prediction.probability || [0.5, 0.5],
          confidence: prediction.confidence || 0.5,
          method: prediction.method || 'single',
          modelCount: prediction.model_count || 1,
          modelIds: prediction.model_ids || [selectedModel.value],
          agreement: prediction.agreement, // 投票一致性
          individualPredictions: prediction.individual_predictions // 各模型预测结果
        }
        
        // 获取SHAP解释结果（只对单个模型）
        if (predictionMode.value === 'single') {
          const modelId = selectedModel.value || (prediction.model_ids && prediction.model_ids[0])
          if (modelId) {
            try {
              // 获取单样本SHAP解释
              const instanceShapResponse = await apiService.explainInstance({
                model_id: modelId,
                features: features
              })

              console.log('SHAP单样本解释响应:', instanceShapResponse)

              if (instanceShapResponse.data) {
                shapInstanceData.value = instanceShapResponse.data
                console.log('SHAP单样本数据已设置:', shapInstanceData.value)
                ElMessage.success('SHAP解释分析完成')
              } else if (instanceShapResponse) {
                shapInstanceData.value = instanceShapResponse
                console.log('SHAP单样本数据已设置（直接响应）:', shapInstanceData.value)
                ElMessage.success('SHAP解释分析完成')
              }
              
              // 尝试获取全局特征重要性（后台加载，不影响主流程）
              // 先获取模型信息，看看是否有训练数据文件路径
              apiService.getModelInfo(modelId).then(modelInfo => {
                const modelData = modelInfo.data || modelInfo
                const trainingDataFile =
                  modelData.feature_file ||
                  modelData.metadata?.feature_file ||
                  modelData.training_data_file

                console.log('模型信息:', modelData)
                console.log('训练数据文件路径:', trainingDataFile)

                if (!trainingDataFile) {
                  console.info(
                    '跳过全局 SHAP：模型元数据无训练特征 CSV（常见于从 H5 训练的模型）。单样本 SHAP 仍可用。'
                  )
                  return Promise.resolve(null)
                }

                const shapRequest = {
                  model_id: modelId,
                  n_samples: 50,
                  training_data_file: trainingDataFile
                }

                return apiService.explainGlobal(shapRequest)
              }).then(response => {
                if (!response) return
                console.log('SHAP全局解释响应:', response)
                if (response.data) {
                  shapGlobalData.value = response.data
                  console.log('SHAP全局数据已设置:', shapGlobalData.value)
                } else if (response) {
                  shapGlobalData.value = response
                  console.log('SHAP全局数据已设置（直接响应）:', shapGlobalData.value)
                }
              }).catch(error => {
                console.error('全局SHAP解释失败:', error)
              })
            } catch (error) {
              console.warn('SHAP解释不可用:', error)
              // SHAP解释失败不影响主要功能，只警告
            }
          }
        } else {
          // 集成预测模式下，清空SHAP数据（集成预测暂不支持SHAP）
          shapInstanceData.value = null
          shapGlobalData.value = null
        }
        
        ElMessage.success('分析完成')
        
        // 本地历史：医护/科研等多账号场景按用户隔离；患者账号仅以服务端预测记录为准（与本人 user_id 绑定）
        try {
          let skipLocalHistory = false
          try {
            const u = JSON.parse(localStorage.getItem('user') || 'null')
            if (u && u.role === 'patient') skipLocalHistory = true
          } catch {
            skipLocalHistory = false
          }
          if (!skipLocalHistory) {
            storage.saveHistory({
              ...formData.value,
              bmi: parseFloat(calculatedBMI.value) || 0,
              riskScore: parseFloat(riskScore.value),
              prediction: analysisResult.value.prediction,
              probability: analysisResult.value.probability,
              confidence: analysisResult.value.confidence,
              method: analysisResult.value.method || 'single',
              modelId: predictionMode.value === 'single' ? selectedModel.value : null,
              modelIds: predictionMode.value === 'ensemble' ? selectedModels.value : null,
              modelCount: analysisResult.value.modelCount || 1,
              features: features // 保存使用的特征向量
            })
          }
        } catch (error) {
          console.warn('保存历史记录失败:', error)
        }
      } catch (error) {
        ElMessage.error(`分析失败: ${error.message}`)
        activeTab.value = 'info'
      } finally {
        analyzing.value = false
      }
    }


    // H5信号图表渲染
    const renderSignalCharts = async () => {
      const { nextTick } = await import('vue')
      const echarts = await import('echarts')
      await nextTick()
      signalCharts.forEach(c => c.dispose())
      signalCharts = []
      const s = h5Signals.value
      if (!s) return

      const lineOpt = (timeArr, dataArr, color, yUnit) => ({
        tooltip: { trigger: 'axis', formatter: (p) => `${(+p[0].value[0]).toFixed(1)} ms<br/>${p[0].marker}${(+p[0].value[1]).toFixed(4)} ${yUnit}` },
        grid: { left: 60, right: 20, top: 10, bottom: 40 },
        xAxis: { type: 'value', name: 'ms', nameLocation: 'end', min: timeArr[0], max: timeArr[timeArr.length - 1] },
        yAxis: { type: 'value', name: yUnit },
        series: [{ type: 'line', data: timeArr.map((t, i) => [t, dataArr[i]]), symbol: 'none', lineStyle: { color, width: 1 }, areaStyle: { color: color + '22' } }],
        dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 5 }]
      })

      if (s.ecg && monitorEcgRef.value) {
        const c = echarts.init(monitorEcgRef.value)
        c.setOption(lineOpt(s.ecg.time, s.ecg.data, '#409EFF', 'mV'))
        signalCharts.push(c)
      }
      if (s.icg && monitorIcgRef.value) {
        const c = echarts.init(monitorIcgRef.value)
        c.setOption(lineOpt(s.icg.time, s.icg.data, '#67C23A', 'Ω'))
        signalCharts.push(c)
      }
      if (s.icg && monitorDzRef.value) {
        const c = echarts.init(monitorDzRef.value)
        c.setOption(lineOpt(s.icg.time, s.icg.dz, '#E6A23C', ''))
        signalCharts.push(c)
      }
      if (s.echo && monitorEchoRef.value) {
        const echo = s.echo
        const canvas = monitorEchoRef.value
        canvas.width = echo.width
        canvas.height = echo.height
        const ctx = canvas.getContext('2d')
        const imgData = ctx.createImageData(echo.width, echo.height)
        for (let row = 0; row < echo.height; row++) {
          for (let col = 0; col < echo.width; col++) {
            const v = echo.data[row][col]
            const idx = (row * echo.width + col) * 4
            imgData.data[idx]     = Math.min(255, v < 128 ? 0 : (v - 128) * 2)
            imgData.data[idx + 1] = Math.min(255, v < 128 ? v * 2 : 255)
            imgData.data[idx + 2] = Math.min(255, v < 64 ? v * 4 : Math.max(0, 255 - (v - 64) * 3))
            imgData.data[idx + 3] = 255
          }
        }
        ctx.putImageData(imgData, 0, 0)
      }
    }

    // 监听h5Signals变化，自动渲染图表

    return {
      formRef,
      recordPatientId,
      selectedModel,
      selectedModels,
      modelList,
      loadingModels,
      loadModelList,
      getModelDisplayName,
      getModelTypeName,
      getModelTypeTag,
      predictionMode,
      ensembleMethod,
      handlePredictionModeChange,
      uploadRef,
      activeTab,
      analyzing,
      analysisResult,
      shapInstanceData,
      shapGlobalData,
      formData,
      rules,
      calculatedBMI,
      hasResult,
      riskScore,
      riskLevel,
      riskClass,
      riskIcon,
      riskIconClass,
      riskProgressColor,
      handleFileChange,
      handleFileRemove,
      h5Signals,
      monitorEcgRef,
      monitorIcgRef,
      monitorDzRef,
      monitorEchoRef,
      renderSignalCharts,
      handleUploadAndExtract,
      applyExtractedFeatures,
      formatFileSize,
      resetForm,
      handleTabChange,
      submitForm,
      exportResults,
      exportPDFReport,
      printResults,
      formatLabelWithAbbr,
      getAbbreviationTooltip,
      uploading,
      extracting,
      extractedFeatures,
      selectedFile,
      Refresh,
      RefreshLeft,
      Check,
      Document,
      Printer
    }
  }
}
</script>

<style scoped>
.risk-switch-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
  align-items: center;
}

.monitor-hero-card :deep(.el-card__header) {
  background: var(--hc-fill-elevated, linear-gradient(180deg, #fafbfc 0%, #fff 100%));
  border-bottom: 1px solid #f0f2f5;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.card-header .el-icon {
  margin-right: 10px;
  font-size: 24px;
  color: #409eff;
}

.monitor-form {
  max-width: 1000px;
  margin: 0 auto;
  padding: 30px 0;
}

:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
  padding-right: 20px;
  line-height: 32px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

:deep(.el-form-item__label span) {
  display: inline-block;
}

/* HRV特征标签两行显示时的对齐 */
:deep(.el-form-item__label > div) {
  text-align: right;
}

:deep(.el-form-item__content) {
  line-height: 32px;
}

:deep(.el-divider) {
  margin: 32px 0;
  border-color: #e4e7ed;
}

:deep(.el-divider__text) {
  background-color: #fff;
  padding: 0 20px;
  font-weight: 600;
  color: #606266;
  font-size: 15px;
}

.analyzing {
  padding: 60px 40px;
  text-align: center;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.result-content {
  padding: 30px;
}

:deep(.el-tabs) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-tabs__header) {
  margin: 0;
  background: #fff;
}

:deep(.el-tabs__item) {
  font-weight: 500;
  padding: 0 32px;
  height: 50px;
  line-height: 50px;
  font-size: 15px;
}

:deep(.el-tabs__content) {
  padding: 30px;
}

.risk-card {
  text-align: center;
  padding: 40px 30px;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.risk-card.risk-low {
  background: linear-gradient(135deg, #f0f9ff 0%, #e1f5fe 100%);
  border: 2px solid #67c23a;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.15);
}

.risk-card.risk-medium {
  background: linear-gradient(135deg, #fff7e6 0%, #ffecc7 100%);
  border: 2px solid #e6a23c;
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.15);
}

.risk-card.risk-high {
  background: linear-gradient(135deg, #fef0f0 0%, #ffe6e6 100%);
  border: 2px solid #f56c6c;
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.2);
}

.risk-header {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30px;
  gap: 20px;
}

.risk-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.risk-icon-wrapper .risk-icon-low {
  color: #67c23a;
}

.risk-icon-wrapper .risk-icon-medium {
  color: #e6a23c;
}

.risk-icon-wrapper .risk-icon-high {
  color: #f56c6c;
}

.risk-title-section {
  text-align: left;
}

.risk-title-section h2 {
  margin: 0 0 10px 0;
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.risk-level {
  font-size: 36px;
  font-weight: bold;
  margin: 0;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.risk-card.risk-medium .risk-level {
  background: linear-gradient(135deg, #e6a23c 0%, #f0a020 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.risk-card.risk-high .risk-level {
  background: linear-gradient(135deg, #f56c6c 0%, #ff4d4f 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.risk-visualization {
  margin-top: 30px;
}

.risk-score-section {
  margin-bottom: 20px;
}

.score-label {
  font-size: 16px;
  color: #606266;
  margin-bottom: 8px;
}

.score-value {
  font-size: 48px;
  font-weight: bold;
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.risk-card.risk-medium .score-value {
  background: linear-gradient(135deg, #e6a23c 0%, #f0a020 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.risk-card.risk-high .score-value {
  background: linear-gradient(135deg, #f56c6c 0%, #ff4d4f 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.risk-progress {
  margin: 20px 0;
  border-radius: 10px;
  overflow: hidden;
}

.risk-indicator {
  display: flex;
  justify-content: space-around;
  margin-top: 20px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 8px;
}

.indicator-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #909399;
  transition: all 0.3s ease;
}

.indicator-item.active {
  color: #303133;
  font-weight: 600;
}

.indicator-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.indicator-dot.low {
  background: #67c23a;
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.5);
}

.indicator-dot.medium {
  background: #e6a23c;
  box-shadow: 0 0 8px rgba(230, 162, 60, 0.5);
}

.indicator-dot.high {
  background: #f56c6c;
  box-shadow: 0 0 8px rgba(245, 108, 108, 0.5);
}

.probability-distribution {
  margin-top: 30px;
  padding-top: 30px;
  border-top: 2px dashed rgba(0, 0, 0, 0.1);
}

.prob-item {
  margin-bottom: 20px;
}

.prob-item:last-child {
  margin-bottom: 0;
}

.prob-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.prob-label .el-icon {
  font-size: 18px;
}

.prob-bar-wrapper {
  width: 100%;
  height: 36px;
  background: #f5f7fa;
  border-radius: 18px;
  overflow: hidden;
  position: relative;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

.prob-bar {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 12px;
  transition: width 1s ease;
  border-radius: 18px;
}

.prob-bar-low {
  background: linear-gradient(90deg, #67c23a 0%, #85ce61 100%);
}

.prob-bar-high {
  background: linear-gradient(90deg, #f56c6c 0%, #ff7875 100%);
}

.prob-value {
  color: #fff;
  font-weight: bold;
  font-size: 14px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.no-result {
  padding: 60px;
  text-align: center;
}

.file-info {
  margin-top: 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.extracted-features {
  margin-top: 10px;
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

.prediction-details-card {
  border-radius: 8px;
}

.prediction-details-card :deep(.el-card__header) {
  padding: 18px 20px;
  border-bottom: 2px solid #f0f2f5;
}

:deep(.el-descriptions) {
  margin-top: 10px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
}

.warning-card {
  border-left: 4px solid #f56c6c;
  background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
}

.success-card {
  border-left: 4px solid #67c23a;
  background: linear-gradient(135deg, #f0f9ff 0%, #fff 100%);
}

.warning-content,
.success-content {
  padding: 10px 0;
}

.recommendations {
  margin-top: 20px;
}

.recommendation-item {
  display: flex;
  gap: 15px;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  margin-bottom: 15px;
  transition: all 0.3s ease;
}

.recommendation-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.recommendation-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.recommendation-icon.medical {
  background: linear-gradient(135deg, #fef0f0 0%, #ffe6e6 100%);
  color: #f56c6c;
}

.recommendation-icon.diet {
  background: linear-gradient(135deg, #fff7e6 0%, #ffecc7 100%);
  color: #e6a23c;
}

.recommendation-icon.exercise {
  background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
  color: #409eff;
}

.recommendation-icon.monitor {
  background: linear-gradient(135deg, #f0f9ff 0%, #d4edda 100%);
  color: #67c23a;
}

.recommendation-content {
  flex: 1;
}

.recommendation-content h5 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.recommendation-content p {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #606266;
}

.health-tips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media print {
  .card-actions {
    display: none;
  }
  
  .risk-card,
  .prediction-details-card,
  .warning-card,
  .success-card {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  
  .recommendation-item {
    break-inside: avoid;
    page-break-inside: avoid;
  }
}
</style>

