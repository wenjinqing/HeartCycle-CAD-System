<template>
  <div class="system-monitor-container hc-page-shell">
    <el-card class="header-card hc-card-elevated" shadow="never">
      <h2>系统监控</h2>
    </el-card>

    <!-- 系统状态概览 -->
    <el-row :gutter="20" class="status-cards">
      <el-col :span="6">
        <el-card class="status-card">
          <div class="status-item">
            <div class="status-icon cpu">
              <el-icon><Cpu /></el-icon>
            </div>
            <div class="status-info">
              <div class="status-label">CPU使用率</div>
              <div class="status-value">{{ cpuPercent }}%</div>
              <el-progress
                :percentage="cpuPercent"
                :color="getProgressColor(cpuPercent)"
                :show-text="false"
              />
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="status-card">
          <div class="status-item">
            <div class="status-icon memory">
              <el-icon><Memo /></el-icon>
            </div>
            <div class="status-info">
              <div class="status-label">内存使用率</div>
              <div class="status-value">{{ memoryPercent }}%</div>
              <el-progress
                :percentage="memoryPercent"
                :color="getProgressColor(memoryPercent)"
                :show-text="false"
              />
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="status-card">
          <div class="status-item">
            <div class="status-icon disk">
              <el-icon><FolderOpened /></el-icon>
            </div>
            <div class="status-info">
              <div class="status-label">磁盘使用率</div>
              <div class="status-value">{{ diskPercent }}%</div>
              <el-progress
                :percentage="diskPercent"
                :color="getProgressColor(diskPercent)"
                :show-text="false"
              />
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="status-card">
          <div class="status-item">
            <div class="status-icon uptime">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="status-info">
              <div class="status-label">运行时间</div>
              <div class="status-value small">{{ uptime }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 告警信息 -->
    <el-card class="alerts-card" v-if="alerts.length > 0">
      <template #header>
        <div class="card-header">
          <span>系统告警</span>
          <el-badge :value="alerts.length" type="danger" />
        </div>
      </template>
      <el-alert
        v-for="(alert, index) in alerts"
        :key="index"
        :title="alert.message"
        :type="alert.level === 'critical' ? 'error' : 'warning'"
        :closable="false"
        style="margin-bottom: 10px"
      >
        <template #default>
          <div>阈值: {{ alert.threshold }}% | 当前值: {{ alert.value }}%</div>
          <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
        </template>
      </el-alert>
    </el-card>

    <!-- 详细信息 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="detail-card">
          <template #header>
            <span>CPU信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="使用率">
              {{ systemStatus.cpu?.percent }}%
            </el-descriptions-item>
            <el-descriptions-item label="核心数">
              {{ systemStatus.cpu?.count }}
            </el-descriptions-item>
            <el-descriptions-item label="当前频率">
              {{ systemStatus.cpu?.frequency?.current }} MHz
            </el-descriptions-item>
          </el-descriptions>

          <!-- CPU历史图表 -->
          <div ref="cpuChartRef" style="height: 200px; margin-top: 20px"></div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="detail-card">
          <template #header>
            <span>内存信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="总内存">
              {{ systemStatus.memory?.total_gb }} GB
            </el-descriptions-item>
            <el-descriptions-item label="已使用">
              {{ systemStatus.memory?.used_gb }} GB
            </el-descriptions-item>
            <el-descriptions-item label="可用">
              {{ systemStatus.memory?.available_gb }} GB
            </el-descriptions-item>
            <el-descriptions-item label="使用率">
              {{ systemStatus.memory?.percent }}%
            </el-descriptions-item>
          </el-descriptions>

          <!-- 内存历史图表 -->
          <div ref="memoryChartRef" style="height: 200px; margin-top: 20px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card class="detail-card">
          <template #header>
            <span>磁盘信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="总容量">
              {{ systemStatus.disk?.total_gb }} GB
            </el-descriptions-item>
            <el-descriptions-item label="已使用">
              {{ systemStatus.disk?.used_gb }} GB
            </el-descriptions-item>
            <el-descriptions-item label="可用">
              {{ systemStatus.disk?.free_gb }} GB
            </el-descriptions-item>
            <el-descriptions-item label="使用率">
              {{ systemStatus.disk?.percent }}%
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="detail-card">
          <template #header>
            <span>进程信息</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="进程ID">
              {{ systemStatus.process?.pid }}
            </el-descriptions-item>
            <el-descriptions-item label="CPU使用率">
              {{ systemStatus.process?.cpu_percent }}%
            </el-descriptions-item>
            <el-descriptions-item label="内存使用">
              {{ systemStatus.process?.memory_mb }} MB
            </el-descriptions-item>
            <el-descriptions-item label="线程数">
              {{ systemStatus.process?.num_threads }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              {{ systemStatus.process?.status }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card class="detail-card">
          <template #header>
            <span>网络信息</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="发送数据">
              {{ systemStatus.network?.bytes_sent_mb }} MB
            </el-descriptions-item>
            <el-descriptions-item label="接收数据">
              {{ systemStatus.network?.bytes_recv_mb }} MB
            </el-descriptions-item>
            <el-descriptions-item label="发送包数">
              {{ systemStatus.network?.packets_sent }}
            </el-descriptions-item>
            <el-descriptions-item label="接收包数">
              {{ systemStatus.network?.packets_recv }}
            </el-descriptions-item>
            <el-descriptions-item label="发送错误">
              {{ systemStatus.network?.errors_out }}
            </el-descriptions-item>
            <el-descriptions-item label="接收错误">
              {{ systemStatus.network?.errors_in }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
// eslint-disable-next-line no-unused-vars
import { Cpu, Memo, FolderOpened, Clock } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { api } from '@/services/api'

const systemStatus = ref({})
const alerts = ref([])
const history = ref({ cpu: [], memory: [], disk: [] })
const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
let cpuChart = null
let memoryChart = null
let refreshTimer = null

const cpuPercent = computed(() => systemStatus.value.cpu?.percent || 0)
const memoryPercent = computed(() => systemStatus.value.memory?.percent || 0)
const diskPercent = computed(() => systemStatus.value.disk?.percent || 0)
const uptime = computed(() => systemStatus.value.uptime?.formatted || '-')

// 加载系统状态
const loadSystemStatus = async () => {
  try {
    const response = await api.get('/monitor/status')
    console.log('监控响应:', response)
    console.log('响应数据:', response.data)
    systemStatus.value = response.data
    console.log('systemStatus.value:', systemStatus.value)
  } catch (error) {
    console.error('加载系统状态失败:', error)
  }
}

// 加载告警信息
const loadAlerts = async () => {
  try {
    const response = await api.get('/monitor/alerts')
    alerts.value = response.data.alerts || []
  } catch (error) {
    console.error('加载告警信息失败:', error)
  }
}

// 加载历史数据
const loadHistory = async () => {
  try {
    const response = await api.get('/monitor/history')
    history.value = response.data
    updateCharts()
  } catch (error) {
    console.error('加载历史数据失败:', error)
  }
}

// 初始化CPU图表
const initCpuChart = () => {
  if (!cpuChartRef.value) return

  cpuChart = echarts.init(cpuChartRef.value)
  const option = {
    title: { text: 'CPU使用率历史', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{
      name: 'CPU',
      type: 'line',
      smooth: true,
      data: [],
      areaStyle: { opacity: 0.3 }
    }]
  }
  cpuChart.setOption(option)
}

// 初始化内存图表
const initMemoryChart = () => {
  if (!memoryChartRef.value) return

  memoryChart = echarts.init(memoryChartRef.value)
  const option = {
    title: { text: '内存使用率历史', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{
      name: '内存',
      type: 'line',
      smooth: true,
      data: [],
      areaStyle: { opacity: 0.3 }
    }]
  }
  memoryChart.setOption(option)
}

// 更新图表
const updateCharts = () => {
  if (cpuChart && history.value.cpu) {
    const times = history.value.cpu.map(item =>
      new Date(item.timestamp).toLocaleTimeString()
    )
    const values = history.value.cpu.map(item => item.percent)

    cpuChart.setOption({
      xAxis: { data: times },
      series: [{ data: values }]
    })
  }

  if (memoryChart && history.value.memory) {
    const times = history.value.memory.map(item =>
      new Date(item.timestamp).toLocaleTimeString()
    )
    const values = history.value.memory.map(item => item.percent)

    memoryChart.setOption({
      xAxis: { data: times },
      series: [{ data: values }]
    })
  }
}

// 获取进度条颜色
const getProgressColor = (percent) => {
  if (percent < 60) return '#67c23a'
  if (percent < 80) return '#e6a23c'
  return '#f56c6c'
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

// 刷新数据
const refreshData = async () => {
  await Promise.all([
    loadSystemStatus(),
    loadAlerts(),
    loadHistory()
  ])
}

onMounted(async () => {
  await refreshData()

  // 初始化图表
  setTimeout(() => {
    initCpuChart()
    initMemoryChart()
    updateCharts()
  }, 100)

  // 定时刷新（每5秒）
  refreshTimer = setInterval(refreshData, 5000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  if (cpuChart) {
    cpuChart.dispose()
  }
  if (memoryChart) {
    memoryChart.dispose()
  }
})
</script>

<style scoped>
.system-monitor-container {
  padding-top: 4px;
}

.header-card {
  margin-bottom: 20px;
}

.header-card h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.status-cards {
  margin-bottom: 20px;
}

.status-card {
  height: 100%;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 15px;
}

.status-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: white;
}

.status-icon.cpu {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.status-icon.memory {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.status-icon.disk {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.status-icon.uptime {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.status-info {
  flex: 1;
}

.status-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

.status-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.status-value.small {
  font-size: 16px;
}

.alerts-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-time {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.detail-card {
  margin-bottom: 20px;
}
</style>
