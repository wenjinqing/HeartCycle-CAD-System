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

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card class="feature-card">
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
        <el-card class="feature-card">
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
        <el-card class="feature-card">
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

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Guide /></el-icon>
              <span>快速开始</span>
            </div>
          </template>
          <el-steps :active="0" align-center>
            <el-step title="填写体征信息" description="输入年龄、性别、BMI等基本信息" />
            <el-step title="上传ECG数据" description="上传HDF5格式的心电数据文件（可选）" />
            <el-step title="开始分析" description="系统自动提取特征并进行风险评估" />
            <el-step title="查看结果" description="获得详细的风险评估报告和预警信息" />
          </el-steps>
          <div style="text-align: center; margin-top: 40px">
            <el-button type="primary" size="large" @click="$router.push('/monitor')" style="padding: 15px 40px; font-size: 16px">
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
import { DataAnalysis, Warning, Document, Guide, Right } from '@element-plus/icons-vue'

export default {
  name: 'Home',
  components: {
    DataAnalysis,
    Warning,
    Document,
    Guide,
    Right
  }
}
</script>

<style scoped>
.home {
  max-width: 1200px;
  margin: 0 auto;
}

.welcome-card {
  text-align: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.welcome-content h1 {
  font-size: 40px;
  margin-bottom: 15px;
  font-weight: 600;
  letter-spacing: 1px;
}

.subtitle {
  font-size: 20px;
  opacity: 0.95;
  font-weight: 300;
}

.feature-card {
  height: 100%;
  transition: all 0.3s ease;
  border: 1px solid #e4e7ed;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
  border-color: #409eff;
}

.card-header {
  display: flex;
  align-items: center;
  font-weight: bold;
}

.card-header .el-icon {
  margin-right: 8px;
  font-size: 20px;
  color: #409eff;
}

.feature-card p {
  color: #606266;
  line-height: 1.8;
  font-size: 15px;
  margin: 0;
}
</style>


