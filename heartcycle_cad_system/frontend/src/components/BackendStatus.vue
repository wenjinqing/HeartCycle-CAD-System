<template>
  <div v-if="showStatus" class="backend-status" :class="statusClass">
    <span class="status-dot" :class="`dot-${status}`" aria-hidden="true" />
    <span class="status-text">{{ statusText }}</span>
    <span v-if="apiUrl" class="status-url">{{ apiUrl }}</span>
  </div>
</template>

<script>
import { getLastDetectedPort, checkBackendPort } from '@/utils/backendDetector'

export default {
  name: 'BackendStatus',
  data() {
    return {
      status: 'checking', // checking, connected, disconnected
      apiUrl: '',
      showStatus: true,
      checkInterval: null
    }
  },
  computed: {
    statusClass() {
      return `status-${this.status}`
    },
    statusText() {
      switch (this.status) {
        case 'checking':
          return '检测后端服务...'
        case 'connected':
          return '后端已连接'
        case 'disconnected':
          return '后端未连接'
        default:
          return '未知状态'
      }
    }
  },
  mounted() {
    this.checkBackendStatus()
    // 每30秒检查一次
    this.checkInterval = setInterval(() => {
      this.checkBackendStatus()
    }, 30000)
  },
  beforeUnmount() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
    }
  },
  methods: {
    async checkBackendStatus() {
      const port = getLastDetectedPort()
      if (port) {
        this.apiUrl = `localhost:${port}`
        const isAvailable = await checkBackendPort(port)
        this.status = isAvailable ? 'connected' : 'disconnected'
      } else {
        this.status = 'checking'
        this.apiUrl = ''
      }

      // 连接成功后3秒隐藏状态
      if (this.status === 'connected') {
        setTimeout(() => {
          this.showStatus = false
        }, 3000)
      } else {
        this.showStatus = true
      }
    }
  }
}
</script>

<style scoped>
.backend-status {
  position: fixed;
  top: 10px;
  right: 10px;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 9999;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.status-checking {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
}

.status-connected {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-disconnected {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-checking {
  background-color: #856404;
  animation: pulse-dot 1s ease-in-out infinite;
}

.dot-connected {
  background-color: #28a745;
}

.dot-disconnected {
  background-color: #c82333;
}

@keyframes pulse-dot {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.status-text {
  font-weight: 500;
}

.status-url {
  font-size: 12px;
  opacity: 0.8;
  font-family: monospace;
}
</style>
