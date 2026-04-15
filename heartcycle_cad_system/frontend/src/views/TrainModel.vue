<template>
  <div class="train-model hc-page-shell">
    <el-card class="hc-card-elevated" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon><Setting /></el-icon>
          <span>模型训练</span>
        </div>
      </template>

      <el-steps :active="currentStep" finish-status="success" align-center style="margin-bottom: 0">
        <el-step title="上传数据" description="上传特征和标签文件" />
        <el-step title="配置参数" description="设置模型训练参数" />
        <el-step title="训练模型" description="执行模型训练" />
        <el-step title="查看结果" description="查看训练结果" />
      </el-steps>

      <div class="step-content">
        <!-- 步骤1: 选择训练模式并上传数据 -->
        <div v-if="currentStep === 0" class="step-panel">
          <el-form label-width="160px">
            <el-form-item label="训练模式">
              <el-radio-group v-model="trainingMode" @change="handleTrainingModeChange">
                <el-radio value="csv">从CSV文件训练（特征+标签）</el-radio>
                <el-radio value="h5">从H5文件训练（ECG原始数据）</el-radio>
              </el-radio-group>
            </el-form-item>

            <!-- CSV模式：特征和标签文件上传 -->
            <template v-if="trainingMode === 'csv'">
              <el-form-item label="特征文件 (CSV)">
              <el-upload
                ref="featureUploadRef"
                :auto-upload="false"
                :on-change="handleFeatureFileChange"
                :on-remove="handleFeatureFileRemove"
                :limit="1"
                accept=".csv"
              >
                <el-button type="primary">
                  <el-icon><Upload /></el-icon>
                  选择特征文件
                </el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    CSV格式，包含特征列。必需列：age（年龄）、gender（性别：M/F）、height（身高cm）、weight（体重kg）。可选列：bmi（BMI指数）、mean_rr（平均RR间期，ms）、sdnn（正常RR间期标准差，ms）、rmssd（连续RR间期差值均方根，ms）、pnn50（RR间期差异超过50ms百分比，%）、lf_hf_ratio（LF/HF比值，HRV频域特征）
                  </div>
                </template>
              </el-upload>
              <div v-if="featureFile" class="file-info">
                <el-tag type="info" style="margin-top: 10px">
                  <el-icon><Document /></el-icon>
                  {{ featureFile.name }} ({{ formatFileSize(featureFile.size) }})
                </el-tag>
              </div>
            </el-form-item>

            <el-form-item label="标签文件 (CSV)">
              <el-upload
                ref="labelUploadRef"
                :auto-upload="false"
                :on-change="handleLabelFileChange"
                :on-remove="handleLabelFileRemove"
                :limit="1"
                accept=".csv"
              >
                <el-button type="primary">
                  <el-icon><Upload /></el-icon>
                  选择标签文件
                </el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    CSV格式，包含一列标签（0=健康，1=CAD）
                  </div>
                </template>
              </el-upload>
              <div v-if="labelFile" class="file-info">
                <el-tag type="info" style="margin-top: 10px">
                  <el-icon><Document /></el-icon>
                  {{ labelFile.name }} ({{ formatFileSize(labelFile.size) }})
                </el-tag>
              </div>
            </el-form-item>
            </template>

            <!-- H5模式：数据目录和元数据文件上传 -->
            <template v-if="trainingMode === 'h5'">
              <el-form-item label="H5数据文件">
                <div style="display: flex; flex-direction: column; gap: 10px">
                  <!-- 方式1：通过文件管理器选择多个H5文件 -->
                  <el-upload
                    ref="h5FilesUploadRef"
                    :auto-upload="false"
                    :on-change="handleH5FilesChange"
                    :on-remove="handleH5FilesRemove"
                    multiple
                    accept=".h5"
                    :limit="100"
                  >
                    <el-button type="primary">
                      <el-icon><FolderOpened /></el-icon>
                      选择H5文件（可多选）
                    </el-button>
                    <template #tip>
                      <div class="el-upload__tip">
                        支持选择多个H5文件进行批量训练，系统会自动上传到服务器
                      </div>
                    </template>
                  </el-upload>
                  
                  <!-- 显示已选择的文件列表 -->
                  <div v-if="selectedH5Files && selectedH5Files.length > 0" class="h5-files-list">
                    <el-tag 
                      v-for="(file, index) in selectedH5Files" 
                      :key="index"
                      closable
                      @close="removeH5File(index)"
                      style="margin: 5px 5px 5px 0"
                    >
                      <el-icon><Document /></el-icon>
                      {{ file.name }} ({{ formatFileSize(file.size) }})
                    </el-tag>
                    <div style="margin-top: 10px">
                      <el-text type="success">已选择 {{ selectedH5Files.length }} 个H5文件</el-text>
                    </div>
                  </div>
                  
                  <!-- 或者：手动输入目录路径（仅在未选择文件时显示） -->
                  <template v-if="selectedH5Files.length === 0">
                    <el-divider>
                      <el-text type="info">或手动输入目录路径</el-text>
                    </el-divider>
                    
                    <el-input
                      v-model="h5DataDir"
                      placeholder="请输入H5文件所在的目录路径（相对于服务器）"
                      style="width: 400px"
                    >
                      <template #prepend>data/raw</template>
                    </el-input>
                    <div class="el-form-item__tip" style="margin-top: 5px; color: #909399; font-size: 12px">
                      如果H5文件已在服务器上，可直接输入目录路径；否则请使用上方文件选择器上传
                    </div>
                  </template>
                </div>
              </el-form-item>

              <el-form-item label="元数据文件 (CSV（逗号分隔值）, 可选)">
                <el-upload
                  ref="metadataUploadRef"
                  :auto-upload="false"
                  :on-change="handleMetadataFileChange"
                  :on-remove="handleMetadataFileRemove"
                  :limit="1"
                  accept=".csv"
                >
                  <el-button type="primary">
                    <el-icon><Upload /></el-icon>
                    选择元数据文件
                  </el-button>
                  <template #tip>
                    <div class="el-upload__tip">
                      CSV格式，包含受试者信息和标签（Subject_ID, Age_years, Disease_Status等）
                    </div>
                  </template>
                </el-upload>
                <div v-if="metadataFile" class="file-info">
                  <el-tag type="info" style="margin-top: 10px">
                    <el-icon><Document /></el-icon>
                    {{ metadataFile.name }} ({{ formatFileSize(metadataFile.size) }})
                  </el-tag>
                </div>
                <div v-if="uploadedMetadataFile" class="file-info" style="margin-top: 5px">
                  <el-tag type="success">已上传: {{ uploadedMetadataFile }}</el-tag>
                </div>
              </el-form-item>

              <el-form-item label="标签文件 (CSV（逗号分隔值）, 可选)">
                <el-upload
                  ref="h5LabelUploadRef"
                  :auto-upload="false"
                  :on-change="handleH5LabelFileChange"
                  :on-remove="handleH5LabelFileRemove"
                  :limit="1"
                  accept=".csv"
                >
                  <el-button type="primary">
                    <el-icon><Upload /></el-icon>
                    选择标签文件
                  </el-button>
                  <template #tip>
                    <div class="el-upload__tip">
                      CSV格式，包含文件名和标签列（如果提供，将优先于元数据中的标签）
                    </div>
                  </template>
                </el-upload>
                <div v-if="h5LabelFile" class="file-info">
                  <el-tag type="info" style="margin-top: 10px">
                    <el-icon><Document /></el-icon>
                    {{ h5LabelFile.name }} ({{ formatFileSize(h5LabelFile.size) }})
                  </el-tag>
                </div>
                <div v-if="uploadedH5LabelFile" class="file-info" style="margin-top: 5px">
                  <el-tag type="success">已上传: {{ uploadedH5LabelFile }}</el-tag>
                </div>
              </el-form-item>

              <el-form-item label="特征提取选项">
                <el-checkbox v-model="h5Config.use_existing_rpeaks">使用已有R波标注</el-checkbox>
                <el-checkbox v-model="h5Config.extract_hrv" style="margin-left: 20px">提取HRV（心率变异性）特征</el-checkbox>
                <el-checkbox v-model="h5Config.extract_clinical" style="margin-left: 20px">提取临床特征</el-checkbox>
              </el-form-item>
            </template>

            <el-form-item>
              <el-button 
                v-if="trainingMode === 'csv'"
                type="primary" 
                size="large" 
                @click="uploadFiles" 
                :loading="uploading" 
                :disabled="!featureFile || !labelFile"
              >
                <el-icon v-if="!uploading"><Upload /></el-icon>
                {{ uploading ? '上传中...' : '上传并继续' }}
              </el-button>
              <el-button 
                v-else
                type="primary" 
                size="large" 
                @click="handleH5TrainingPrepare" 
                :loading="preparingH5" 
                :disabled="selectedH5Files.length === 0 && !h5DataDir"
              >
                <el-icon v-if="!preparingH5"><Right /></el-icon>
                {{ preparingH5 ? '准备中...' : '继续配置' }}
              </el-button>
              <el-button size="large" @click="currentStep = 0" style="margin-left: 10px">
                <el-icon><RefreshLeft /></el-icon>
                重新选择
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤2: 配置参数 -->
        <div v-if="currentStep === 1" class="step-panel">
          <el-form :model="trainConfig" label-width="160px">
            <el-form-item label="模型类型">
                <el-radio-group v-model="trainConfig.model_type">
                <el-radio value="lr">逻辑回归 (LR)</el-radio>
                <el-radio value="svm">支持向量机 (SVM)</el-radio>
                <el-radio value="rf">随机森林 (RF)</el-radio>
                <el-radio value="xgb">XGBoost (推荐)</el-radio>
                <el-radio value="lgb">LightGBM</el-radio>
                <el-radio value="stacking">Stacking集成</el-radio>
                <el-radio value="voting">Voting集成</el-radio>
              </el-radio-group>
              <div style="margin-top: 10px; font-size: 12px; color: #909399">
                <p v-if="trainConfig.model_type === 'xgb'">XGBoost: 高性能梯度提升算法，通常有最好的预测效果</p>
                <p v-if="trainConfig.model_type === 'lgb'">LightGBM: 训练速度快，内存占用少</p>
                <p v-if="trainConfig.model_type === 'stacking'">Stacking: 组合多个模型，提升预测精度</p>
                <p v-if="trainConfig.model_type === 'voting'">Voting: 多个模型投票决策，稳定性好</p>
              </div>
            </el-form-item>

            <el-form-item label="数据平衡处理">
              <el-switch
                v-model="trainConfig.use_smote"
                active-text="启用SMOTE"
                inactive-text="禁用"
              />
              <div style="margin-top: 5px; font-size: 12px; color: #909399">
                SMOTE可以处理类别不平衡问题，提升少数类的识别率
              </div>
            </el-form-item>

            <el-form-item label="超参数优化">
              <el-switch
                v-model="trainConfig.optimize_hyperparams"
                active-text="启用自动优化"
                inactive-text="使用默认参数"
                :disabled="['stacking', 'voting'].includes(trainConfig.model_type)"
              />
              <div style="margin-top: 5px; font-size: 12px; color: #909399">
                <span v-if="!['stacking', 'voting'].includes(trainConfig.model_type)">
                  自动搜索最佳超参数组合，可能需要较长时间（建议数据量较大时使用）
                </span>
                <span v-else style="color: #F56C6C">
                  集成模型不支持超参数优化
                </span>
              </div>
            </el-form-item>

            <el-form-item label="交叉验证折数">
              <el-input-number
                v-model="trainConfig.cv_folds"
                :min="2"
                :max="10"
                style="width: 200px"
              />
              <span style="margin-left: 10px; color: #909399">推荐: 5</span>
            </el-form-item>

            <el-form-item label="随机种子">
              <el-input-number
                v-model="trainConfig.random_state"
                :min="0"
                style="width: 200px"
              />
            </el-form-item>

            <el-form-item label="模型名称">
              <el-input
                v-model="trainConfig.display_name"
                maxlength="100"
                show-word-limit
                clearable
                placeholder="展示在「模型版本管理」；留空则使用「类型_训练模型」"
                style="width: 400px"
              />
            </el-form-item>

            <el-form-item label="模型描述">
              <el-input
                v-model="trainConfig.description"
                type="textarea"
                :rows="3"
                maxlength="2000"
                show-word-limit
                placeholder="可选：说明数据范围、实验目的等，将在模型版本管理页展示"
                style="width: 400px"
              />
            </el-form-item>

              <el-form-item>
              <el-button 
                type="primary" 
                size="large" 
                @click="currentStep = 2" 
                :disabled="trainingMode === 'csv' ? (!uploadedFeatureFile || !uploadedLabelFile) : (selectedH5Files.length === 0 && !h5DataDir && !uploadedH5DataDir)"
              >
                <el-icon><Right /></el-icon>
                下一步：配置参数
              </el-button>
              <el-button size="large" @click="currentStep = 0" style="margin-left: 20px">
                <el-icon><ArrowLeft /></el-icon>
                返回上一步
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤3: 训练模型 -->
        <div v-if="currentStep === 2" class="step-panel">
          <!-- 准备训练状态 -->
          <div v-if="!trainingStarted && !training && !trainingResult">
            <el-card>
              <template #header>
                <span>训练配置确认</span>
              </template>
              <el-descriptions :column="2" border style="margin-bottom: 20px">
                <template v-if="trainingMode === 'csv'">
                  <el-descriptions-item label="训练模式">CSV文件训练</el-descriptions-item>
                  <el-descriptions-item label="特征文件">
                    {{ uploadedFeatureFile || '未上传' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="标签文件">
                    {{ uploadedLabelFile || '未上传' }}
                  </el-descriptions-item>
                </template>
                <template v-else>
                  <el-descriptions-item label="训练模式">H5文件训练</el-descriptions-item>
                  <el-descriptions-item label="数据目录">
                    {{ (uploadedH5DataDir || h5DataDir) || '未设置' }}
                  </el-descriptions-item>
                  <el-descriptions-item v-if="selectedH5Files.length > 0" label="已选择文件数">
                    {{ selectedH5Files.length }} 个H5文件
                  </el-descriptions-item>
                  <el-descriptions-item label="元数据文件">
                    {{ uploadedMetadataFile || '未上传（可选）' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="标签文件">
                    {{ uploadedH5LabelFile || '未上传（可选）' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="使用R波标注">
                    {{ h5Config.use_existing_rpeaks ? '是' : '否' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="提取HRV特征">
                    {{ h5Config.extract_hrv ? '是' : '否' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="提取临床特征">
                    {{ h5Config.extract_clinical ? '是' : '否' }}
                  </el-descriptions-item>
                </template>
                <el-descriptions-item label="模型类型">
                  {{ getModelTypeName(trainConfig.model_type) }}
                </el-descriptions-item>
                <el-descriptions-item label="交叉验证">
                  {{ trainConfig.cv_folds }}折
                </el-descriptions-item>
                <el-descriptions-item label="随机种子">
                  {{ trainConfig.random_state }}
                </el-descriptions-item>
                <el-descriptions-item label="模型名称（管理页）" :span="2">
                  {{ trainConfig.display_name?.trim() || '（默认名称）' }}
                </el-descriptions-item>
                <el-descriptions-item label="模型描述" :span="2">
                  {{ trainConfig.description?.trim() || '—' }}
                </el-descriptions-item>
              </el-descriptions>
              <div style="text-align: center; margin-top: 30px">
                <el-button 
                  type="primary" 
                  size="large" 
                  @click="startTraining" 
                  :disabled="trainingMode === 'csv' ? (!uploadedFeatureFile || !uploadedLabelFile) : (selectedH5Files.length === 0 && !h5DataDir && !uploadedH5DataDir)" 
                  :loading="training"
                >
                  <el-icon v-if="!training"><VideoPlay /></el-icon>
                  {{ training ? '训练中...' : '开始训练模型' }}
                </el-button>
                <el-button size="large" @click="currentStep = 1" style="margin-left: 20px">
                  <el-icon><ArrowLeft /></el-icon>
                  返回上一步
                </el-button>
              </div>
            </el-card>
          </div>

          <!-- 训练中状态 -->
          <div v-else-if="training" class="training-status">
            <el-result icon="info">
              <template #icon>
                <el-icon class="is-loading" :size="60"><Loading /></el-icon>
              </template>
              <template #title>{{ trainingMessage || '正在训练模型...' }}</template>
              <template #sub-title>
                <div v-if="trainingMode === 'h5' && totalFiles > 0" style="margin-top: 10px">
                  <el-progress 
                    :percentage="Math.round(trainingProgress)" 
                    :status="trainingProgress === 100 ? 'success' : undefined"
                    style="width: 400px; margin: 0 auto;"
                  />
                  <p style="margin-top: 10px; color: #909399">
                    已处理 {{ processedFiles }} / {{ totalFiles }} 个文件
                  </p>
                  <p v-if="currentFile" style="margin-top: 5px; color: #909399; font-size: 12px">
                    当前文件: {{ currentFile }}
                  </p>
                </div>
                <div v-else style="margin-top: 10px">
                  <el-progress 
                    :percentage="Math.round(trainingProgress)" 
                    :status="trainingProgress === 100 ? 'success' : undefined"
                    style="width: 400px; margin: 0 auto;"
                  />
                </div>
                <p style="margin-top: 15px; color: #909399">
                  请稍候，训练可能需要几分钟时间
                </p>
              </template>
            </el-result>
          </div>

          <!-- 训练结果状态 -->
          <div v-else-if="trainingResult" class="training-result">
              <el-alert
                :title="trainingResult.success ? '训练成功' : '训练失败'"
                :type="trainingResult.success ? 'success' : 'error'"
                :closable="false"
                show-icon
              >
                <template #default v-if="trainingResult.success">
                  <p><strong>模型ID:</strong> {{ trainingResult.model_id }}</p>
                  <p v-if="trainingResult.metrics">
                    <strong>AUC（曲线下面积）:</strong> {{ trainingResult.metrics.roc_auc?.mean?.toFixed(4) || 'N/A' }}
                  </p>
                  <p v-if="trainingResult.metrics">
                    <strong>准确率:</strong> {{ trainingResult.metrics.accuracy?.mean?.toFixed(4) || 'N/A' }}
                  </p>
                </template>
                <template #default v-else>
                  <p><strong>错误信息:</strong> {{ trainingResult.error || '未知错误' }}</p>
                  <p v-if="trainingResult.errorDetails" style="margin-top: 10px; color: #909399; font-size: 12px">
                    {{ trainingResult.errorDetails }}
                  </p>
                </template>
              </el-alert>
              <div style="margin-top: 20px">
                <el-button type="primary" size="large" @click="viewResults">
                  <el-icon><ViewIcon /></el-icon>
                  查看详细结果
                </el-button>
                <el-button size="large" @click="resetTraining" style="margin-left: 10px">
                  <el-icon><RefreshLeft /></el-icon>
                  重新训练
                </el-button>
              </div>
              <div
                v-if="trainingResult.success && canPublishToRegistry"
                class="publish-registry-inline"
                style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #ebeef5"
              >
                <el-checkbox v-model="versionPublishSetActive">登记同时设为该名称下的激活版本</el-checkbox>
                <div style="margin-top: 10px">
                  <el-button
                    type="success"
                    :loading="publishingToRegistry"
                    @click="publishTrainingToModelVersions"
                  >
                    保存并发布到模型版本
                  </el-button>
                  <el-button text type="primary" @click="openModelVersions">打开模型版本页</el-button>
                </div>
              </div>
          </div>
        </div>

        <!-- 步骤4: 查看结果 -->
        <div v-if="currentStep === 3" class="step-panel">
          <el-card v-if="trainingResult && trainingResult.success">
            <template #header>
              <span>训练结果详情</span>
            </template>

            <el-descriptions :column="2" border>
              <el-descriptions-item label="模型ID">
                <el-tag>{{ trainingResult.model_id }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="模型类型">
                {{ getModelTypeName(trainingResult.model_type) }}
              </el-descriptions-item>
              <el-descriptions-item label="样本数">
                {{ trainingResult.n_samples }}
              </el-descriptions-item>
              <el-descriptions-item label="特征数">
                {{ trainingResult.n_features }}
              </el-descriptions-item>
            </el-descriptions>

            <el-divider>性能指标</el-divider>

            <!-- 性能指标卡片 -->
            <el-row :gutter="20" style="margin-top: 20px">
              <el-col :span="6" v-for="metric in metricsCards" :key="metric.key">
                <div class="metric-card">
                  <div class="metric-label">{{ metric.label }}</div>
                  <div class="metric-value">{{ metric.value }}</div>
                  <div class="metric-cv" v-if="metric.cv">{{ metric.cv }}</div>
                </div>
              </el-col>
            </el-row>

            <!-- 性能指标表格 -->
            <el-table :data="metricsTable" style="margin-top: 20px" border stripe>
              <el-table-column prop="metric" label="指标" width="150" />
              <el-table-column prop="mean" label="均值" width="150" align="center" />
              <el-table-column prop="std" label="标准差" width="150" align="center" />
            </el-table>

            <!-- 交叉验证分数可视化 -->
            <el-divider>交叉验证分数分布</el-divider>
            <div ref="cvScoresChartRef" style="width: 100%; height: 400px; margin-top: 20px"></div>

            <!-- 性能雷达图 -->
            <el-divider>综合性能雷达图</el-divider>
            <div ref="performanceRadarRef" style="width: 100%; height: 400px; margin-top: 20px"></div>

            <!-- SHAP全局特征重要性 -->
            <ShapExplanation
              v-if="shapGlobalData"
              :global-importance="shapGlobalData"
              style="margin-top: 20px"
            />

            <el-divider v-if="trainingResult && trainingResult.success && canPublishToRegistry">模型版本发布</el-divider>
            <div
              v-if="trainingResult && trainingResult.success && canPublishToRegistry"
              class="publish-registry-block"
              style="margin-bottom: 20px"
            >
              <p style="color: #606266; font-size: 13px; margin: 0 0 12px">
                将本次训练的 joblib 复制到模型版本库，便于在「模型版本」页统一管理与设为激活预测模型。
              </p>
              <el-checkbox v-model="versionPublishSetActive">登记同时设为该名称下的激活版本</el-checkbox>
              <div style="margin-top: 12px">
                <el-button
                  type="success"
                  size="large"
                  :loading="publishingToRegistry"
                  @click="publishTrainingToModelVersions"
                >
                  保存并发布到模型版本
                </el-button>
                <el-button size="large" @click="openModelVersions">打开模型版本页</el-button>
              </div>
            </div>

            <div style="margin-top: 30px">
              <el-button type="primary" size="large" @click="goToMonitor">
                <el-icon><Right /></el-icon>
                使用模型进行预测
              </el-button>
              <el-button size="large" @click="resetTraining" style="margin-left: 10px">
                <el-icon><Plus /></el-icon>
                训练新模型
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, Upload, Document, VideoPlay, Loading, RefreshLeft, Right, ArrowLeft, View as ViewIcon, Plus, FolderOpened } from '@element-plus/icons-vue'
import { apiService } from '../services/api'
import ShapExplanation from '../components/ShapExplanation.vue'
import * as echarts from 'echarts'

export default {
  name: 'TrainModel',
  components: {
    Setting,
    Upload,
    Document,
    VideoPlay,
    Loading,
    RefreshLeft,
    Right,
    ArrowLeft,
    ViewIcon,
    Plus,
    FolderOpened,
    ShapExplanation
  },
  setup() {
    const router = useRouter()
    const currentStep = ref(0)
    const trainingMode = ref('csv') // 'csv' 或 'h5'
    const featureUploadRef = ref(null)
    const labelUploadRef = ref(null)
    const metadataUploadRef = ref(null)
    const h5LabelUploadRef = ref(null)
    const h5FilesUploadRef = ref(null)
    const featureFile = ref(null)
    const labelFile = ref(null)
    const metadataFile = ref(null)
    const h5LabelFile = ref(null)
    const selectedH5Files = ref([])
    const uploadedH5DataDir = ref('')
    const h5DataDir = ref('')
    const uploading = ref(false)
    const preparingH5 = ref(false)
    const uploadedFeatureFile = ref('')
    const uploadedLabelFile = ref('')
    const uploadedMetadataFile = ref('')
    const uploadedH5LabelFile = ref('')
    const training = ref(false)
    const trainingStarted = ref(false)
    const trainingResult = ref(null)
    const versionPublishSetActive = ref(true)
    const publishingToRegistry = ref(false)
    const shapGlobalData = ref(null)
    const trainingTaskId = ref(null)
    const trainingProgress = ref(0)
    const trainingMessage = ref('')
    const currentFile = ref(null)
    const processedFiles = ref(0)
    const totalFiles = ref(0)
    const progressPolling = ref(null)

    // 图表引用
    const cvScoresChartRef = ref(null)
    const performanceRadarRef = ref(null)
    let cvScoresChart = null
    let performanceRadarChart = null

    const trainConfig = ref({
      model_type: 'xgb',  // 默认使用XGBoost
      cv_folds: 5,
      random_state: 42,
      use_smote: true,  // 默认启用SMOTE
      optimize_hyperparams: false,  // 默认不启用超参数优化
      display_name: '',
      description: ''
    })

    const h5Config = ref({
      use_existing_rpeaks: true,
      extract_hrv: true,
      extract_clinical: true
    })

    const handleFeatureFileChange = (file) => {
      if (file.raw) {
        featureFile.value = file.raw
      }
    }

    const handleFeatureFileRemove = () => {
      featureFile.value = null
      uploadedFeatureFile.value = ''
    }

    const handleLabelFileChange = (file) => {
      if (file.raw) {
        labelFile.value = file.raw
      }
    }

    const handleLabelFileRemove = () => {
      labelFile.value = null
      uploadedLabelFile.value = ''
    }

    const handleMetadataFileChange = (file) => {
      if (file.raw) {
        metadataFile.value = file.raw
      }
    }

    const handleMetadataFileRemove = () => {
      metadataFile.value = null
      uploadedMetadataFile.value = ''
    }

    const handleH5LabelFileChange = (file) => {
      if (file.raw) {
        h5LabelFile.value = file.raw
      }
    }

    const handleH5LabelFileRemove = () => {
      h5LabelFile.value = null
      uploadedH5LabelFile.value = ''
    }

    const handleH5FilesChange = (file, fileList) => {
      // 更新选中的文件列表（只保留原始文件对象）
      selectedH5Files.value = fileList.map(item => item.raw).filter(Boolean)
    }

    const handleH5FilesRemove = (file, fileList) => {
      // 更新选中的文件列表
      selectedH5Files.value = fileList.map(item => item.raw).filter(Boolean)
      // 如果文件被移除，清空已上传的目录
      if (selectedH5Files.value.length === 0) {
        uploadedH5DataDir.value = ''
        h5DataDir.value = ''
      }
    }

    const removeH5File = (index) => {
      if (!selectedH5Files.value || selectedH5Files.value.length === 0) {
        return
      }
      
      if (index >= 0 && index < selectedH5Files.value.length) {
        selectedH5Files.value.splice(index, 1)
        
        // 更新上传组件的文件列表
        if (h5FilesUploadRef.value && h5FilesUploadRef.value.fileList) {
          const fileList = h5FilesUploadRef.value.fileList
          if (index >= 0 && index < fileList.length) {
            fileList.splice(index, 1)
          }
        }
      }
      
      // 如果文件被移除完，清空已上传的目录
      if (selectedH5Files.value.length === 0) {
        uploadedH5DataDir.value = ''
        h5DataDir.value = ''
      }
    }

    const handleH5TrainingPrepare = async () => {
      // H5模式：选择文件后直接进入配置页面，文件在开始训练时自动上传
      if (selectedH5Files.value.length > 0 || h5DataDir.value) {
        // 如果有元数据文件或标签文件，先上传这些文件
        try {
          preparingH5.value = true
          
          // 上传元数据文件（如果提供）
          if (metadataFile.value) {
            ElMessage.info('正在上传元数据文件...')
            const metadataResponse = await apiService.uploadFile(metadataFile.value)
            let metadataResult = metadataResponse
            if (metadataResponse.data) {
              metadataResult = metadataResponse.data
            } else if (metadataResponse.file_path) {
              metadataResult = metadataResponse
            }
            uploadedMetadataFile.value = metadataResult.file_path
          }

          // 上传标签文件（如果提供）
          if (h5LabelFile.value) {
            ElMessage.info('正在上传标签文件...')
            const h5LabelResponse = await apiService.uploadFile(h5LabelFile.value)
            let h5LabelResult = h5LabelResponse
            if (h5LabelResponse.data) {
              h5LabelResult = h5LabelResponse.data
            } else if (h5LabelResponse.file_path) {
              h5LabelResult = h5LabelResponse
            }
            uploadedH5LabelFile.value = h5LabelResult.file_path
          }
          
          // 直接进入配置页面，H5文件在开始训练时自动上传
          currentStep.value = 1
          ElMessage.success('已准备好，请配置训练参数')
        } catch (error) {
          ElMessage.error(`文件上传失败: ${error.message}`)
          console.error('上传错误:', error)
        } finally {
          preparingH5.value = false
        }
      } else {
        ElMessage.warning('请选择H5文件或输入H5数据目录路径')
      }
    }

    const handleTrainingModeChange = () => {
      // 切换训练模式时重置所有文件
      featureFile.value = null
      labelFile.value = null
      metadataFile.value = null
      h5LabelFile.value = null
      selectedH5Files.value = []
      uploadedH5DataDir.value = ''
      h5DataDir.value = ''
      uploadedFeatureFile.value = ''
      uploadedLabelFile.value = ''
      uploadedMetadataFile.value = ''
      uploadedH5LabelFile.value = ''
      featureUploadRef.value?.clearFiles()
      labelUploadRef.value?.clearFiles()
      metadataUploadRef.value?.clearFiles()
      h5LabelUploadRef.value?.clearFiles()
      h5FilesUploadRef.value?.clearFiles()
    }

    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
    }

    const uploadFiles = async () => {
      if (trainingMode.value === 'csv') {
        if (!featureFile.value || !labelFile.value) {
          ElMessage.warning('请选择特征文件和标签文件')
          return
        }

        try {
          uploading.value = true

          // 上传特征文件
          ElMessage.info('正在上传特征文件...')
          const featureResponse = await apiService.uploadFile(featureFile.value)
          let featureResult = featureResponse
          if (featureResponse.data) {
            featureResult = featureResponse.data
          } else if (featureResponse.file_path) {
            featureResult = featureResponse
          }
          uploadedFeatureFile.value = featureResult.file_path

          // 上传标签文件
          ElMessage.info('正在上传标签文件...')
          const labelResponse = await apiService.uploadFile(labelFile.value)
          let labelResult = labelResponse
          if (labelResponse.data) {
            labelResult = labelResponse.data
          } else if (labelResponse.file_path) {
            labelResult = labelResponse
          }
          uploadedLabelFile.value = labelResult.file_path

          uploading.value = false
          ElMessage.success('文件上传成功，请配置训练参数')
          currentStep.value = 1
        } catch (error) {
          uploading.value = false
          ElMessage.error(`文件上传失败: ${error.message}`)
          console.error('上传错误:', error)
        }
      } else {
        // H5模式
        try {
          uploading.value = true

          // H5模式下，如果还没有上传文件，先上传
          if (selectedH5Files.value.length > 0 && !uploadedH5DataDir.value && !h5DataDir.value) {
            ElMessage.info(`正在上传 ${selectedH5Files.value.length} 个H5文件...`)
            
            // 批量上传H5文件
            const uploadResponse = await apiService.uploadH5Batch(selectedH5Files.value)
            const uploadResult = uploadResponse.data || uploadResponse
            
            if (uploadResult.success && uploadResult.data) {
              uploadedH5DataDir.value = uploadResult.data.data_dir
              h5DataDir.value = uploadResult.data.data_dir
              ElMessage.success(`成功上传 ${uploadResult.data.file_count} 个H5文件`)
            } else {
              throw new Error(uploadResult.message || '上传失败')
            }
          }
          
          // 检查是否有有效的数据目录（上传后的目录或手动输入的目录）
          if (!h5DataDir.value && !uploadedH5DataDir.value) {
            ElMessage.warning('请选择H5文件或输入H5数据目录路径')
            uploading.value = false
            return
          }

          // 上传元数据文件（如果提供）
          if (metadataFile.value) {
            ElMessage.info('正在上传元数据文件...')
            const metadataResponse = await apiService.uploadFile(metadataFile.value)
            let metadataResult = metadataResponse
            if (metadataResponse.data) {
              metadataResult = metadataResponse.data
            } else if (metadataResponse.file_path) {
              metadataResult = metadataResponse
            }
            uploadedMetadataFile.value = metadataResult.file_path
          }

          // 上传标签文件（如果提供）
          if (h5LabelFile.value) {
            ElMessage.info('正在上传标签文件...')
            const h5LabelResponse = await apiService.uploadFile(h5LabelFile.value)
            let h5LabelResult = h5LabelResponse
            if (h5LabelResponse.data) {
              h5LabelResult = h5LabelResponse.data
            } else if (h5LabelResponse.file_path) {
              h5LabelResult = h5LabelResponse
            }
            uploadedH5LabelFile.value = h5LabelResult.file_path
          }

          uploading.value = false
          ElMessage.success('准备完成，请配置训练参数')
          currentStep.value = 1
        } catch (error) {
          uploading.value = false
          ElMessage.error(`文件上传失败: ${error.message}`)
          console.error('上传错误:', error)
        }
      }
    }

    const getModelTypeName = (type) => {
      const names = {
        'lr': '逻辑回归',
        'svm': '支持向量机',
        'rf': '随机森林',
        'xgb': 'XGBoost',
        'lgb': 'LightGBM',
        'stacking': 'Stacking集成',
        'voting': 'Voting集成'
      }
      return names[type] || type
    }

    const startTraining = async () => {
      try {
        training.value = true
        trainingStarted.value = true

        ElMessage.info('开始训练模型，请稍候...')

        let response
        if (trainingMode.value === 'csv') {
          response = await apiService.trainModel({
            feature_file: uploadedFeatureFile.value,
            label_file: uploadedLabelFile.value,
            model_type: trainConfig.value.model_type,
            cv_folds: trainConfig.value.cv_folds,
            random_state: trainConfig.value.random_state,
            use_smote: trainConfig.value.use_smote,
            optimize_hyperparams: trainConfig.value.optimize_hyperparams,
            display_name: trainConfig.value.display_name?.trim() || undefined,
            model_description: trainConfig.value.description?.trim() || undefined
          })
        } else {
          // H5模式 - 如果选择了文件但还没有上传，先上传
          let dataDir = uploadedH5DataDir.value || h5DataDir.value
          
          if (!dataDir && selectedH5Files.value.length > 0) {
            ElMessage.info('正在上传H5文件...')
            try {
              const uploadResponse = await apiService.uploadH5Batch(selectedH5Files.value)
              
              // 响应拦截器已经处理了响应，返回的是data字段的内容
              // 原始响应格式: {success: true, data: {data_dir: '...', ...}}
              // 拦截器处理后: {data_dir: '...', batch_id: '...', ...}
              let uploadResult = uploadResponse
              
              // 如果响应拦截器已经处理，uploadResponse 就是 data 字段的内容
              // 如果还没有处理，需要从 uploadResponse.data 获取
              if (uploadResponse && typeof uploadResponse === 'object') {
                // 检查是否有 data_dir 字段（说明已经是处理后的格式）
                if (uploadResponse.data_dir) {
                  uploadResult = uploadResponse
                } 
                // 检查是否有嵌套的 data 字段（说明是原始格式）
                else if (uploadResponse.data && uploadResponse.data.data_dir) {
                  uploadResult = uploadResponse.data
                }
                // 检查是否有 success 字段（说明是原始格式，但 data 可能为空）
                else if (uploadResponse.success && uploadResponse.data) {
                  uploadResult = uploadResponse.data
                }
              }
              
              // 直接检查 data_dir 字段
              if (uploadResult && uploadResult.data_dir) {
                uploadedH5DataDir.value = uploadResult.data_dir
                h5DataDir.value = uploadResult.data_dir
                dataDir = uploadResult.data_dir
                ElMessage.success(`成功上传 ${uploadResult.file_count || 1} 个H5文件，开始训练...`)
              } else {
                throw new Error('上传失败：响应格式不正确，无法获取数据目录路径')
              }
            } catch (error) {
              training.value = false
              trainingStarted.value = false
              ElMessage.error(`H5文件上传失败: ${error.message}`)
              console.error('上传错误:', error)
              return
            }
          }
          
          if (!dataDir) {
            training.value = false
            trainingStarted.value = false
            ElMessage.error('请选择H5文件或输入H5数据目录路径')
            return
          }
          
          // 启动异步任务
          response = await apiService.trainModelFromH5({
            data_dir: dataDir,
            metadata_file: uploadedMetadataFile.value || null,
            label_file: uploadedH5LabelFile.value || null,
            model_type: trainConfig.value.model_type,
            cv_folds: trainConfig.value.cv_folds,
            random_state: trainConfig.value.random_state,
            use_smote: trainConfig.value.use_smote,
            optimize_hyperparams: trainConfig.value.optimize_hyperparams,
            use_existing_rpeaks: h5Config.value.use_existing_rpeaks,
            extract_hrv: h5Config.value.extract_hrv,
            extract_clinical: h5Config.value.extract_clinical,
            display_name: trainConfig.value.display_name?.trim() || undefined,
            model_description: trainConfig.value.description?.trim() || undefined
          })
          
          // 处理响应：响应拦截器可能已经处理了格式
          let result = response
          if (response && typeof response === 'object') {
            // 如果响应有data字段，使用data字段
            if (response.data && response.data.task_id) {
              result = response.data
            } else if (response.task_id) {
              result = response
            } else if (response.data) {
              result = response.data
            }
          }
          
          if (!result || !result.task_id) {
            throw new Error('未获取到训练任务ID，请检查后端响应')
          }
          
          trainingTaskId.value = result.task_id
          ElMessage.success('H5训练任务已启动，正在处理...')
          
          // 开始轮询任务状态
          startProgressPolling()
          return // H5模式异步处理，直接返回
        }

        // CSV模式 - 同步处理
        const result = response.data || response
        trainingResult.value = {
          success: true,
          ...result
        }

        training.value = false
        ElMessage.success('模型训练成功！')
        currentStep.value = 3

        // 等待DOM更新后初始化图表
        nextTick(() => {
          initCharts()
        })

        // 获取SHAP全局特征重要性（后台加载）
        if (result.model_id) {
          try {
            // 如果有上传的特征文件路径，传递给后端
            const shapRequest = {
              model_id: result.model_id,
              n_samples: 100
            }

            // 只有在有特征文件路径时才传递
            if (uploadedFeatureFile.value) {
              shapRequest.training_data_file = uploadedFeatureFile.value
            }

            const shapResponse = await apiService.explainGlobal(shapRequest)
            if (shapResponse.data) {
              shapGlobalData.value = shapResponse.data
            }
          } catch (error) {
            console.warn('获取SHAP全局解释失败:', error)
            // SHAP解释失败不影响训练结果
          }
        }
      } catch (error) {
        training.value = false
        trainingStarted.value = false
        ElMessage.error(`模型训练失败: ${error.message}`)
        trainingResult.value = {
          success: false,
          error: error.message
        }
      }
    }

    const viewResults = () => {
      currentStep.value = 3
      // 等待DOM更新后初始化图表
      nextTick(() => {
        initCharts()
      })
    }

    const canPublishToRegistry = computed(() => {
      try {
        const raw = localStorage.getItem('user')
        if (!raw) return false
        const u = JSON.parse(raw)
        const r = (u.role || '').toLowerCase()
        return r === 'admin' || r === 'researcher'
      } catch {
        return false
      }
    })

    const openModelVersions = () => {
      router.push('/model-versions')
    }

    const publishTrainingToModelVersions = async () => {
      if (!trainingResult.value?.success || !trainingResult.value.model_id) {
        ElMessage.warning('暂无可用训练结果')
        return
      }
      publishingToRegistry.value = true
      try {
        const res = await apiService.registerTrainingToModelVersions({
          model_id: trainingResult.value.model_id,
          model_type: trainingResult.value.model_type,
          display_name: trainConfig.value.display_name || undefined,
          model_description: trainConfig.value.description || undefined,
          n_samples: trainingResult.value.n_samples,
          n_features: trainingResult.value.n_features,
          metrics: trainingResult.value.metrics,
          feature_names: trainingResult.value.feature_names,
          set_active: versionPublishSetActive.value
        })
        ElMessage.success(res.message || '已发布到模型版本')
      } catch (error) {
        ElMessage.error(error.userMessage || error.message || '发布到模型版本失败')
      } finally {
        publishingToRegistry.value = false
      }
    }

    // 初始化图表
    const initCharts = () => {
      if (!trainingResult.value || !trainingResult.value.metrics) return

      // 初始化交叉验证分数图表
      if (cvScoresChartRef.value) {
        if (cvScoresChart) {
          cvScoresChart.dispose()
        }
        cvScoresChart = echarts.init(cvScoresChartRef.value)
        updateCVScoresChart()
      }

      // 初始化性能雷达图
      if (performanceRadarRef.value) {
        if (performanceRadarChart) {
          performanceRadarChart.dispose()
        }
        performanceRadarChart = echarts.init(performanceRadarRef.value)
        updatePerformanceRadar()
      }
    }

    // 更新交叉验证分数图表
    const updateCVScoresChart = () => {
      if (!cvScoresChart || !trainingResult.value?.metrics) return

      const metrics = trainingResult.value.metrics
      const categories = []
      const data = []

      // 提取每个指标的交叉验证分数
      if (metrics.accuracy?.cv_scores) {
        categories.push('准确率')
        data.push({
          name: '准确率',
          type: 'box',
          data: [metrics.accuracy.cv_scores]
        })
      }
      if (metrics.precision?.cv_scores) {
        categories.push('精确率')
        data.push({
          name: '精确率',
          type: 'box',
          data: [metrics.precision.cv_scores]
        })
      }
      if (metrics.recall?.cv_scores) {
        categories.push('召回率')
        data.push({
          name: '召回率',
          type: 'box',
          data: [metrics.recall.cv_scores]
        })
      }
      if (metrics.f1?.cv_scores) {
        categories.push('F1分数')
        data.push({
          name: 'F1分数',
          type: 'box',
          data: [metrics.f1.cv_scores]
        })
      }
      if (metrics.roc_auc?.cv_scores) {
        categories.push('ROC-AUC')
        data.push({
          name: 'ROC-AUC',
          type: 'box',
          data: [metrics.roc_auc.cv_scores]
        })
      }

      // 如果没有cv_scores，使用柱状图显示均值
      if (data.length === 0) {
        const barData = []
        const barCategories = []

        if (metrics.accuracy?.mean !== undefined) {
          barCategories.push('准确率')
          barData.push(metrics.accuracy.mean)
        }
        if (metrics.precision?.mean !== undefined) {
          barCategories.push('精确率')
          barData.push(metrics.precision.mean)
        }
        if (metrics.recall?.mean !== undefined) {
          barCategories.push('召回率')
          barData.push(metrics.recall.mean)
        }
        if (metrics.f1?.mean !== undefined) {
          barCategories.push('F1分数')
          barData.push(metrics.f1.mean)
        }
        if (metrics.roc_auc?.mean !== undefined) {
          barCategories.push('ROC-AUC')
          barData.push(metrics.roc_auc.mean)
        }

        const option = {
          title: {
            text: '模型性能指标',
            left: 'center'
          },
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'shadow'
            }
          },
          xAxis: {
            type: 'category',
            data: barCategories
          },
          yAxis: {
            type: 'value',
            min: 0,
            max: 1
          },
          series: [{
            name: '分数',
            type: 'bar',
            data: barData,
            itemStyle: {
              color: '#409eff'
            }
          }]
        }
        cvScoresChart.setOption(option)
      } else {
        // 使用箱线图显示交叉验证分数分布
        const option = {
          title: {
            text: '交叉验证分数分布',
            left: 'center'
          },
          tooltip: {
            trigger: 'item',
            axisPointer: {
              type: 'shadow'
            }
          },
          grid: {
            left: '10%',
            right: '10%',
            bottom: '15%'
          },
          xAxis: {
            type: 'category',
            data: categories,
            boundaryGap: true,
            nameGap: 30,
            splitArea: {
              show: false
            },
            splitLine: {
              show: false
            }
          },
          yAxis: {
            type: 'value',
            name: '分数',
            min: 0,
            max: 1,
            splitArea: {
              show: true
            }
          },
          series: data.map((item, index) => ({
            name: item.name,
            type: 'boxplot',
            data: item.data,
            itemStyle: {
              color: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399'][index]
            }
          }))
        }
        cvScoresChart.setOption(option)
      }
    }

    // 更新性能雷达图
    const updatePerformanceRadar = () => {
      if (!performanceRadarChart || !trainingResult.value?.metrics) return

      const metrics = trainingResult.value.metrics
      const indicator = []
      const data = []

      if (metrics.accuracy?.mean !== undefined) {
        indicator.push({ name: '准确率', max: 1 })
        data.push(metrics.accuracy.mean)
      }
      if (metrics.precision?.mean !== undefined) {
        indicator.push({ name: '精确率', max: 1 })
        data.push(metrics.precision.mean)
      }
      if (metrics.recall?.mean !== undefined) {
        indicator.push({ name: '召回率', max: 1 })
        data.push(metrics.recall.mean)
      }
      if (metrics.f1?.mean !== undefined) {
        indicator.push({ name: 'F1分数', max: 1 })
        data.push(metrics.f1.mean)
      }
      if (metrics.roc_auc?.mean !== undefined) {
        indicator.push({ name: 'ROC-AUC', max: 1 })
        data.push(metrics.roc_auc.mean)
      }

      const option = {
        title: {
          text: '模型综合性能',
          left: 'center'
        },
        tooltip: {
          trigger: 'item'
        },
        radar: {
          indicator: indicator,
          shape: 'polygon',
          splitNumber: 5,
          name: {
            textStyle: {
              color: '#606266'
            }
          },
          splitLine: {
            lineStyle: {
              color: '#dcdfe6'
            }
          },
          splitArea: {
            show: true,
            areaStyle: {
              color: ['rgba(64, 158, 255, 0.1)', 'rgba(64, 158, 255, 0.05)']
            }
          },
          axisLine: {
            lineStyle: {
              color: '#dcdfe6'
            }
          }
        },
        series: [{
          name: '性能指标',
          type: 'radar',
          data: [{
            value: data,
            name: getModelTypeName(trainingResult.value.model_type),
            areaStyle: {
              color: 'rgba(64, 158, 255, 0.3)'
            },
            itemStyle: {
              color: '#409eff'
            },
            lineStyle: {
              color: '#409eff',
              width: 2
            }
          }]
        }]
      }
      performanceRadarChart.setOption(option)
    }

    // 性能指标卡片数据
    const metricsCards = computed(() => {
      if (!trainingResult.value || !trainingResult.value.metrics) {
        return []
      }

      const metrics = trainingResult.value.metrics
      const cards = []

      if (metrics.roc_auc) {
        cards.push({
          key: 'roc_auc',
          label: 'ROC-AUC',
          value: metrics.roc_auc.mean?.toFixed(4) || 'N/A',
          cv: metrics.roc_auc.std ? `±${metrics.roc_auc.std.toFixed(4)}` : null
        })
      }

      if (metrics.accuracy) {
        cards.push({
          key: 'accuracy',
          label: '准确率',
          value: metrics.accuracy.mean?.toFixed(4) || 'N/A',
          cv: metrics.accuracy.std ? `±${metrics.accuracy.std.toFixed(4)}` : null
        })
      }

      if (metrics.precision) {
        cards.push({
          key: 'precision',
          label: '精确率',
          value: metrics.precision.mean?.toFixed(4) || 'N/A',
          cv: metrics.precision.std ? `±${metrics.precision.std.toFixed(4)}` : null
        })
      }

      if (metrics.recall) {
        cards.push({
          key: 'recall',
          label: '召回率',
          value: metrics.recall.mean?.toFixed(4) || 'N/A',
          cv: metrics.recall.std ? `±${metrics.recall.std.toFixed(4)}` : null
        })
      }

      return cards
    })

    const startProgressPolling = () => {
      if (progressPolling.value) {
        clearInterval(progressPolling.value)
      }
      
      progressPolling.value = setInterval(async () => {
        if (!trainingTaskId.value) return
        
        try {
          const response = await apiService.getH5TrainingStatus(trainingTaskId.value)
          const status = response.data || response
          
          trainingProgress.value = (status.progress || 0) * 100
          trainingMessage.value = status.message || ''
          currentFile.value = status.current_file
          processedFiles.value = status.processed_files || 0
          totalFiles.value = status.total_files || 0
          
          if (status.status === 'completed') {
            // 训练完成
            clearInterval(progressPolling.value)
            progressPolling.value = null
            
            trainingResult.value = {
              success: true,
              ...status.result
            }
            
            training.value = false
            ElMessage.success('模型训练成功！')
            currentStep.value = 3

            // 等待DOM更新后初始化图表
            nextTick(() => {
              initCharts()
            })

            // 获取SHAP全局特征重要性（后台加载）
            if (status.result?.model_id) {
              try {
                const shapResponse = await apiService.explainGlobal({
                  model_id: status.result.model_id,
                  n_samples: 100
                })
                if (shapResponse.data) {
                  shapGlobalData.value = shapResponse.data
                }
              } catch (error) {
                console.warn('获取SHAP全局解释失败:', error)
              }
            }
          } else if (status.status === 'failed') {
            // 训练失败
            clearInterval(progressPolling.value)
            progressPolling.value = null
            
            training.value = false
            trainingStarted.value = false
            
            const errorMsg = status.error || status.message || '训练失败'
            ElMessage.error(`模型训练失败: ${errorMsg}`)
            
            trainingResult.value = {
              success: false,
              error: errorMsg,
              errorDetails: status.error || status.message
            }
          }
        } catch (error) {
          console.error('查询训练状态失败:', error)
        }
      }, 1000) // 每秒轮询一次
    }

    const resetTraining = () => {
      // 停止轮询
      if (progressPolling.value) {
        clearInterval(progressPolling.value)
        progressPolling.value = null
      }
      
      currentStep.value = 0
      featureFile.value = null
      labelFile.value = null
      metadataFile.value = null
      h5LabelFile.value = null
      uploadedFeatureFile.value = ''
      uploadedLabelFile.value = ''
      uploadedMetadataFile.value = ''
      uploadedH5LabelFile.value = ''
      training.value = false
      trainingStarted.value = false
      trainingResult.value = null
      shapGlobalData.value = null
      trainingTaskId.value = null
      trainingProgress.value = 0
      trainingMessage.value = ''
      currentFile.value = null
      processedFiles.value = 0
      totalFiles.value = 0
      selectedH5Files.value = []
      uploadedH5DataDir.value = ''
      h5DataDir.value = ''
      featureUploadRef.value?.clearFiles()
      labelUploadRef.value?.clearFiles()
      metadataUploadRef.value?.clearFiles()
      h5LabelUploadRef.value?.clearFiles()
      h5FilesUploadRef.value?.clearFiles()
    }

    const goToMonitor = () => {
      router.push('/monitor')
    }

    const metricsTable = computed(() => {
      if (!trainingResult.value || !trainingResult.value.metrics) {
        return []
      }

      const metrics = trainingResult.value.metrics
      const table = []

      if (metrics.accuracy) {
        table.push({
          metric: '准确率 (Accuracy)',
          mean: metrics.accuracy.mean?.toFixed(4) || 'N/A',
          std: metrics.accuracy.std?.toFixed(4) || 'N/A'
        })
      }

      if (metrics.precision) {
        table.push({
          metric: '精确率 (Precision)',
          mean: metrics.precision.mean?.toFixed(4) || 'N/A',
          std: metrics.precision.std?.toFixed(4) || 'N/A'
        })
      }

      if (metrics.recall) {
        table.push({
          metric: '召回率 (Recall)',
          mean: metrics.recall.mean?.toFixed(4) || 'N/A',
          std: metrics.recall.std?.toFixed(4) || 'N/A'
        })
      }

      if (metrics.f1) {
        table.push({
          metric: 'F1分数',
          mean: metrics.f1.mean?.toFixed(4) || 'N/A',
          std: metrics.f1.std?.toFixed(4) || 'N/A'
        })
      }

      if (metrics.roc_auc) {
        table.push({
          metric: 'ROC-AUC',
          mean: metrics.roc_auc.mean?.toFixed(4) || 'N/A',
          std: metrics.roc_auc.std?.toFixed(4) || 'N/A'
        })
      }

      return table
    })

    // 组件卸载时清理轮询和图表
    onUnmounted(() => {
      if (progressPolling.value) {
        clearInterval(progressPolling.value)
      }
      if (cvScoresChart) {
        cvScoresChart.dispose()
        cvScoresChart = null
      }
      if (performanceRadarChart) {
        performanceRadarChart.dispose()
        performanceRadarChart = null
      }
    })

    return {
      currentStep,
      trainingMode,
      featureUploadRef,
      labelUploadRef,
      metadataUploadRef,
      h5LabelUploadRef,
      h5FilesUploadRef,
      featureFile,
      labelFile,
      metadataFile,
      h5LabelFile,
      h5DataDir,
      uploading,
      uploadedFeatureFile,
      uploadedLabelFile,
      uploadedMetadataFile,
      uploadedH5LabelFile,
      selectedH5Files,
      uploadedH5DataDir,
      trainConfig,
      h5Config,
      training,
      trainingStarted,
      trainingResult,
      versionPublishSetActive,
      publishingToRegistry,
      canPublishToRegistry,
      openModelVersions,
      publishTrainingToModelVersions,
      shapGlobalData,
      handleFeatureFileChange,
      handleFeatureFileRemove,
      handleLabelFileChange,
      handleLabelFileRemove,
      handleMetadataFileChange,
      handleMetadataFileRemove,
      handleH5LabelFileChange,
      handleH5LabelFileRemove,
      handleH5FilesChange,
      handleH5FilesRemove,
      removeH5File,
      preparingH5,
      handleH5TrainingPrepare,
      handleTrainingModeChange,
      formatFileSize,
      uploadFiles,
      getModelTypeName,
      startTraining,
      viewResults,
      resetTraining,
      goToMonitor,
      metricsTable,
      metricsCards,
      trainingTaskId,
      trainingProgress,
      trainingMessage,
      currentFile,
      processedFiles,
      totalFiles,
      startProgressPolling,
      cvScoresChartRef,
      performanceRadarRef,
      initCharts
    }
  }
}
</script>

<style scoped>
.train-model {
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
}

:deep(.el-card__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfc;
}

:deep(.el-steps) {
  padding: 30px 20px;
  background: #fafbfc;
  border-radius: 8px;
  margin-bottom: 10px;
}

:deep(.el-step__title) {
  font-size: 16px;
  font-weight: 500;
}

:deep(.el-step__description) {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.step-content {
  margin-top: 40px;
  min-height: 500px;
  padding: 20px 0;
}

.step-panel {
  padding: 30px 40px;
  background: #fff;
  border-radius: 12px;
}

:deep(.el-form-item) {
  margin-bottom: 24px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
  padding-right: 20px;
  line-height: 32px;
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

.file-info {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.training-status {
  padding: 60px 40px;
  text-align: center;
}

.training-result {
  padding: 30px;
  background: #fafbfc;
  border-radius: 12px;
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

:deep(.el-upload) {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
  padding: 40px 20px;
}

:deep(.el-button) {
  border-radius: 6px;
  font-weight: 500;
}

:deep(.el-input) {
  border-radius: 6px;
}

:deep(.el-select) {
  border-radius: 6px;
}

.metric-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  border-radius: 12px;
  color: white;
  text-align: center;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: transform 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-5px);
}

.metric-label {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 4px;
}

.metric-cv {
  font-size: 12px;
  opacity: 0.8;
}

.metric-card:nth-child(2) {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.metric-card:nth-child(3) {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.metric-card:nth-child(4) {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

</style>

