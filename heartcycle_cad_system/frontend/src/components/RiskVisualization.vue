<template>
  <el-card class="risk-card" :class="riskClass">
    <div class="risk-header">
      <div class="risk-icon-wrapper">
        <el-icon :size="50" :class="riskIconClass">
          <component :is="riskIconComponent" />
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
            :style="{ width: (probability[0] * 100) + '%' }"
          >
            <span class="prob-value">{{ (probability[0] * 100).toFixed(1) }}%</span>
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
            :style="{ width: (probability[1] * 100) + '%' }"
          >
            <span class="prob-value">{{ (probability[1] * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script>
import { computed } from 'vue'
import { CircleCheck, Warning, InfoFilled } from '@element-plus/icons-vue'

export default {
  name: 'RiskVisualization',
  components: {
    CircleCheck,
    Warning,
    InfoFilled
  },
  props: {
    probability: {
      type: Array,
      required: true,
      validator: (val) => val.length === 2
    }
  },
  setup(props) {
    const riskScore = computed(() => {
      return (props.probability[1] * 100).toFixed(1)
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

    const riskIconComponent = computed(() => {
      const score = parseFloat(riskScore.value)
      if (score < 30) return CircleCheck
      if (score < 60) return InfoFilled
      return Warning
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

    return {
      riskScore,
      riskLevel,
      riskClass,
      riskIconComponent,
      riskIconClass,
      riskProgressColor
    }
  }
}
</script>

<style scoped>
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
</style>
