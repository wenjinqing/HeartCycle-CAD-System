<template>
  <el-card v-if="isHighRisk" class="warning-card">
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
          <el-col :span="12" v-for="item in recommendations" :key="item.type">
            <div class="recommendation-item">
              <div class="recommendation-icon" :class="item.type">
                <el-icon :size="28"><Document /></el-icon>
              </div>
              <div class="recommendation-content">
                <h5>{{ item.title }}</h5>
                <p>{{ item.description }}</p>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
  </el-card>

  <el-card v-else class="success-card">
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
</template>

<script>
import { computed } from 'vue'
import { Warning, CircleCheck, Document } from '@element-plus/icons-vue'

export default {
  name: 'HealthRecommendations',
  components: {
    Warning,
    CircleCheck,
    Document
  },
  props: {
    prediction: {
      type: Number,
      required: true
    },
    riskScore: {
      type: [Number, String],
      required: true
    }
  },
  setup(props) {
    const isHighRisk = computed(() => props.prediction === 1)

    const recommendations = [
      {
        type: 'medical',
        title: '及时就医检查',
        description: '建议尽快前往心内科进行专业检查，包括心电图、心脏超声、血液检查等，以明确诊断。'
      },
      {
        type: 'diet',
        title: '调整饮食习惯',
        description: '控制盐分和脂肪摄入，减少高胆固醇食物，增加蔬菜水果，保持均衡营养。'
      },
      {
        type: 'exercise',
        title: '适量规律运动',
        description: '每周至少150分钟中等强度有氧运动，如快走、游泳、慢跑，避免剧烈运动。'
      },
      {
        type: 'monitor',
        title: '定期监测复查',
        description: '建议每3-6个月进行一次心血管健康评估，持续监测相关指标变化。'
      }
    ]

    return {
      isHighRisk,
      recommendations
    }
  }
}
</script>

<style scoped>
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
  .recommendation-item {
    break-inside: avoid;
    page-break-inside: avoid;
  }
}
</style>
