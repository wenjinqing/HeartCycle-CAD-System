<template>
  <div class="home">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="welcome-card">
          <div class="welcome-content">
            <h1>欢迎使用 HeartCycle 冠心病风险预测系统</h1>
            <p class="subtitle">基于HeartCycle数据集的智能风险评估平台</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="24" style="margin-top: 30px">
      <el-col :span="8">
        <el-card class="feature-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><DataAnalysis /></el-icon>
              <span>智能分析</span>
            </div>
          </template>
          <p>基于机器学习算法，对HRV特征和临床体征进行综合分析，提供准确的风险评估。</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="feature-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Warning /></el-icon>
              <span>风险预警</span>
            </div>
          </template>
          <p>实时监测和预警，及时发现潜在风险，为健康管理提供科学依据。</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="feature-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>历史记录</span>
            </div>
          </template>
          <p>完整记录每次监测结果，支持历史数据查询和趋势分析。</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- 工具箱 -->
    <el-row :gutter="24" style="margin-top: 30px">
      <el-col :span="24">
        <el-card shadow="never" style="border-radius: 12px">
          <template #header>
            <div class="card-header">
              <el-icon><Tools /></el-icon>
              <span>开发者工具</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="tool-item" @click="$router.push('/train-h5-auto')">
                <el-icon class="tool-icon" color="#409EFF"><Upload /></el-icon>
                <h3>H5快速训练</h3>
                <p>直接上传H5文件进行模型训练</p>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="tool-item" @click="$router.push('/h5-converter')">
                <el-icon class="tool-icon" color="#67C23A"><Tools /></el-icon>
                <h3>H5格式转换</h3>
                <p>MATLAB格式转标准格式</p>
                <el-tag type="success" size="small" style="margin-top: 8px">推荐</el-tag>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="tool-item" @click="$router.push('/train')">
                <el-icon class="tool-icon" color="#E6A23C"><Setting /></el-icon>
                <h3>高级训练</h3>
                <p>完整的模型训练流程</p>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="24" style="margin-top: 30px">
      <el-col :span="24">
        <el-card shadow="never" style="border-radius: 12px">
          <template #header>
            <div class="card-header">
              <el-icon><Guide /></el-icon>
              <span>快速开始</span>
            </div>
          </template>
          <el-steps :active="0" align-center finish-status="success">
            <el-step title="填写体征信息" description="输入年龄、性别、BMI等基本信息" />
            <el-step title="上传ECG数据" description="上传HDF5格式的心电数据文件（可选）" />
            <el-step title="开始分析" description="系统自动提取特征并进行风险评估" />
            <el-step title="查看结果" description="获得详细的风险评估报告和预警信息" />
          </el-steps>
          <div style="text-align: center; margin-top: 50px; padding-bottom: 20px">
            <el-button 
              type="primary" 
              size="large" 
              @click="$router.push('/monitor')" 
              style="padding: 18px 50px; font-size: 18px; border-radius: 8px; font-weight: 500"
            >
              <el-icon><Right /></el-icon>
              立即开始分析
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { DataAnalysis, Warning, Document, Guide, Right, Tools, Upload, Setting } from '@element-plus/icons-vue'

export default {
  name: 'Home',
  components: {
    DataAnalysis,
    Warning,
    Document,
    Guide,
    Right,
    Tools,
    Upload,
    Setting
  }
}
</script>

<style scoped>
.home {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.welcome-card {
  text-align: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 16px;
  padding: 60px 40px;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
  margin-bottom: 30px;
}

.welcome-content h1 {
  font-size: 42px;
  margin-bottom: 20px;
  font-weight: 600;
  letter-spacing: 1px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.subtitle {
  font-size: 20px;
  opacity: 0.95;
  font-weight: 300;
  letter-spacing: 0.5px;
}

.feature-card {
  height: 100%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 0;
  overflow: hidden;
}

.feature-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 12px 32px rgba(64, 158, 255, 0.15);
  border-color: #409eff;
}

.feature-card :deep(.el-card__body) {
  padding: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  font-weight: 600;
  font-size: 16px;
  padding: 16px 0;
}

.card-header .el-icon {
  margin-right: 10px;
  font-size: 22px;
  color: #409eff;
}

.feature-card p {
  color: #606266;
  line-height: 1.8;
  font-size: 15px;
  margin: 0;
  padding-top: 8px;
}

:deep(.el-card) {
  border-radius: 12px;
}

:deep(.el-card__header) {
  border-bottom: 1px solid #f0f2f5;
  padding: 20px;
  background: #fafbfc;
}

:deep(.el-steps) {
  padding: 40px 20px;
}

:deep(.el-step__title) {
  font-size: 16px;
  font-weight: 500;
}

:deep(.el-step__description) {
  font-size: 14px;
  color: #909399;
}

.tool-item {
  text-align: center;
  padding: 30px 20px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s ease;
  background: #fafbfc;
}

.tool-item:hover {
  background: #f0f2f5;
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.tool-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.tool-item h3 {
  font-size: 18px;
  margin: 12px 0 8px 0;
  color: #303133;
}

.tool-item p {
  font-size: 14px;
  color: #909399;
  margin: 0;
}
</style>


