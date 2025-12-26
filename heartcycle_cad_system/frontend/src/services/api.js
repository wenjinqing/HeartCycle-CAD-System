import axios from 'axios'

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    // 如果响应有success字段，检查是否成功
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      if (!response.data.success) {
        const message = response.data.detail || response.data.message || '请求失败'
        return Promise.reject(new Error(message))
      }
    }
    return response.data
  },
  error => {
    // 处理不同类型的错误
    let message = '请求失败'
    
    if (error.response) {
      // 服务器返回了错误响应
      const data = error.response.data
      if (data) {
        if (typeof data === 'object') {
          message = data.detail || data.message || data.error || message
        } else {
          message = data
        }
      }
      message = message || `HTTP ${error.response.status}: ${error.response.statusText}`
    } else if (error.request) {
      // 请求已发出但没有收到响应
      message = '网络错误，请检查网络连接'
    } else {
      // 其他错误
      message = error.message || message
    }
    
    console.error('API Error:', error)
    return Promise.reject(new Error(message))
  }
)

// API方法
export const apiService = {
  // 健康检查
  healthCheck() {
    return axios.get('http://localhost:8000/health')
  },

  // 上传文件
  uploadFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 获取文件列表
  getFiles() {
    return api.get('/files')
  },

  // 提取特征
  extractFeatures(data) {
    return api.post('/extract-features', data)
  },

  // 获取特征提取状态
  getFeatureStatus(taskId) {
    return api.get(`/features/${taskId}`)
  },

  // 训练模型
  trainModel(data) {
    return api.post('/train', data)
  },

  // 获取模型列表
  getModels() {
    return api.get('/models')
  },

  // 获取模型信息
  getModelInfo(modelId) {
    return api.get(`/models/${modelId}`)
  },

  // 预测
  predict(data) {
    return api.post('/predict', data)
  },

  // 集成预测（使用多个模型）
  predictEnsemble(data) {
    return api.post('/predict/ensemble', data)
  },

  // 获取集成模型信息
  getEnsembleInfo(modelIds) {
    return api.post('/ensemble/info', { model_ids: modelIds })
  },

  // SHAP分析
  analyzeSHAP(data) {
    return api.post('/shap/analyze', data)
  },

  // 获取SHAP结果
  getSHAPResults(modelId) {
    return api.get(`/shap/${modelId}`)
  }
}

export default api

