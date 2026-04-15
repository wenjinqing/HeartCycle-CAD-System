<template>
  <div class="h5-visualize hc-page-shell">
    <el-card class="upload-card hc-card-elevated" shadow="never">
      <template #header>
        <span>H5 心电信号可视化</span>
      </template>

      <el-upload
        class="upload-area"
        drag
        :auto-upload="false"
        accept=".h5"
        :limit="1"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
      >
        <el-icon class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">拖拽 .h5 文件到此处，或 <em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">支持 Niccomo 设备导出的 HDF5 格式文件</div>
        </template>
      </el-upload>

      <div style="margin-top: 16px; text-align: center">
        <el-button type="primary" :loading="loading" :disabled="!selectedFile" @click="visualize">
          解析并可视化
        </el-button>
      </div>
    </el-card>

    <template v-if="signals">
      <!-- ECG -->
      <el-card v-if="signals.ecg" class="chart-card hc-card-elevated" shadow="never">
        <template #header>
          <span>ECG 心电图</span>
          <el-tag size="small" style="margin-left: 8px">单位: mV</el-tag>
        </template>
        <div ref="ecgChartRef" style="height: 250px"></div>
      </el-card>

      <!-- ICG -->
      <el-card v-if="signals.icg" class="chart-card hc-card-elevated" shadow="never">
        <template #header>
          <span>ICG 阻抗心动图</span>
          <el-tag size="small" style="margin-left: 8px">单位: Ω</el-tag>
        </template>
        <div ref="icgChartRef" style="height: 250px"></div>
      </el-card>

      <!-- dZ/dt -->
      <el-card v-if="signals.icg" class="chart-card hc-card-elevated" shadow="never">
        <template #header>
          <span>dZ/dt 信号</span>
        </template>
        <div ref="dzChartRef" style="height: 250px"></div>
      </el-card>

      <!-- ECHO -->
      <el-card v-if="signals.echo" class="chart-card hc-card-elevated" shadow="never">
        <template #header>
          <span>超声心动图 (ECHO)</span>
        </template>
        <canvas ref="echoCanvasRef" style="width: 100%; height: 300px; display: block"></canvas>
      </el-card>

      <!-- 错误提示 -->
      <el-alert v-if="signals.ecg_error" :title="'ECG解析失败: ' + signals.ecg_error" type="warning" show-icon />
      <el-alert v-if="signals.icg_error" :title="'ICG解析失败: ' + signals.icg_error" type="warning" show-icon />
      <el-alert v-if="signals.echo_error" :title="'ECHO解析失败: ' + signals.echo_error" type="warning" show-icon />
    </template>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { getApiBaseUrlFast } from '@/utils/backendDetector'

const loading = ref(false)
const selectedFile = ref(null)
const signals = ref(null)

const ecgChartRef = ref(null)
const icgChartRef = ref(null)
const dzChartRef = ref(null)
const echoCanvasRef = ref(null)

let charts = []

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleFileRemove = () => {
  selectedFile.value = null
  signals.value = null
  charts.forEach(c => c.dispose())
  charts = []
}

const visualize = async () => {
  if (!selectedFile.value) return
  loading.value = true
  signals.value = null
  charts.forEach(c => c.dispose())
  charts = []

  try {
    const baseUrl = await getApiBaseUrlFast()
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const token = localStorage.getItem('access_token')
    const res = await axios.post(`${baseUrl}/h5/visualize`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    })

    signals.value = res.data.signals
    await nextTick()
    renderCharts()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '解析失败')
  } finally {
    loading.value = false
  }
}

const lineOption = (title, timeArr, dataArr, color, yUnit) => ({
  tooltip: { trigger: 'axis', formatter: (p) => `${(+p[0].value[0]).toFixed(1)} ms<br/>${p[0].marker}${(+p[0].value[1]).toFixed(4)} ${yUnit}` },
  grid: { left: 60, right: 20, top: 20, bottom: 40 },
  xAxis: { type: 'value', name: 'ms', nameLocation: 'end', min: timeArr[0], max: timeArr[timeArr.length - 1] },
  yAxis: { type: 'value', name: yUnit },
  series: [{
    type: 'line',
    data: timeArr.map((t, i) => [t, dataArr[i]]),
    symbol: 'none',
    lineStyle: { color, width: 1 },
    areaStyle: { color: color + '22' }
  }],
  dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 5 }]
})

const renderCharts = () => {
  const s = signals.value

  if (s.ecg && ecgChartRef.value) {
    const c = echarts.init(ecgChartRef.value)
    c.setOption(lineOption('ECG', s.ecg.time, s.ecg.data, '#409EFF', 'mV'))
    charts.push(c)
  }

  if (s.icg && icgChartRef.value) {
    const c = echarts.init(icgChartRef.value)
    c.setOption(lineOption('ICG', s.icg.time, s.icg.data, '#67C23A', 'Ω'))
    charts.push(c)
  }

  if (s.icg && dzChartRef.value) {
    const c = echarts.init(dzChartRef.value)
    c.setOption(lineOption('dZ/dt', s.icg.time, s.icg.dz, '#E6A23C', ''))
    charts.push(c)
  }

  if (s.echo && echoCanvasRef.value) {
    const echo = s.echo
    const canvas = echoCanvasRef.value
    // 设置实际像素尺寸
    canvas.width = echo.width
    canvas.height = echo.height
    const ctx = canvas.getContext('2d')
    const imgData = ctx.createImageData(echo.width, echo.height)
    // 用viridis风格渲染：黑→绿→白
    for (let row = 0; row < echo.height; row++) {
      for (let col = 0; col < echo.width; col++) {
        const v = echo.data[row][col]  // 0-255
        const idx = (row * echo.width + col) * 4
        // 黑→蓝→青→绿→黄→白 近似viridis
        imgData.data[idx]     = Math.min(255, v < 128 ? 0 : (v - 128) * 2)        // R
        imgData.data[idx + 1] = Math.min(255, v < 128 ? v * 2 : 255)              // G
        imgData.data[idx + 2] = Math.min(255, v < 64 ? v * 4 : Math.max(0, 255 - (v - 64) * 3)) // B
        imgData.data[idx + 3] = 255
      }
    }
    ctx.putImageData(imgData, 0, 0)
  }
}
</script>

<style scoped>
.h5-visualize.hc-page-shell {
  max-width: 1000px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 4px;
}
.upload-card .upload-area {
  width: 100%;
}
.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 8px;
}
.upload-text {
  color: #606266;
  font-size: 14px;
}
.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.chart-card {
  width: 100%;
}
</style>
