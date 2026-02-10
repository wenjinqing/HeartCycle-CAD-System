import axios from 'axios'
import { handleError } from '@/utils/errorHandler'
import { getApiBaseUrlFast, getApiBaseUrl } from '@/utils/backendDetector'

// 默认API地址（如果自动检测失败则使用）
const DEFAULT_API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api/v1'

// 重试配置
const RETRY_CONFIG = {
  maxRetries: 3,           // 最大重试次数
  retryDelay: 1000,        // 重试延迟（毫秒）
  retryDelayMultiplier: 2, // 延迟倍增因子（指数退避）
  retryableStatuses: [408, 429, 500, 502, 503, 504], // 可重试的HTTP状态码
  retryableErrors: ['ECONNABORTED', 'ETIMEDOUT', 'ENOTFOUND', 'ENETUNREACH', 'ERR_NETWORK'] // 可重试的网络错误
}

// 创建axios实例（初始使用默认地址）
const api = axios.create({
  baseURL: DEFAULT_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 延迟函数
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms))

// 判断错误是否可重试
const isRetryableError = (error) => {
  // 网络错误
  if (!error.response && error.code) {
    return RETRY_CONFIG.retryableErrors.includes(error.code)
  }

  // HTTP状态码错误
  if (error.response) {
    return RETRY_CONFIG.retryableStatuses.includes(error.response.status)
  }

  // 超时错误
  if (error.message && error.message.toLowerCase().includes('timeout')) {
    return true
  }

  // CORS错误或网络错误
  if (error.message && (error.message.includes('Network Error') || error.message.includes('CORS'))) {
    return true
  }

  return false
}

// 判断是否是连接错误（需要重新检测端口）
const isConnectionError = (error) => {
  // 没有响应的错误
  if (!error.response) {
    return true
  }

  // CORS错误
  if (error.message && error.message.includes('CORS')) {
    return true
  }

  return false
}

// 重试请求
const retryRequest = async (error) => {
  const config = error.config

  // 如果请求配置了跳过重试，直接拒绝
  if (config.__skipRetry) {
    return Promise.reject(error)
  }

  // 初始化重试计数
  if (!config.__retryCount) {
    config.__retryCount = 0
  }

  // 检查是否超过最大重试次数
  if (config.__retryCount >= RETRY_CONFIG.maxRetries) {
    return Promise.reject(error)
  }

  // 检查是否可重试
  if (!isRetryableError(error)) {
    return Promise.reject(error)
  }

  // 增加重试计数
  config.__retryCount += 1

  // 如果是连接错误，尝试重新检测端口
  if (isConnectionError(error) && config.__retryCount === 1) {
    console.log('🔄 检测到连接错误，尝试重新检测后端端口...')
    try {
      const newBaseUrl = await getApiBaseUrl()
      if (newBaseUrl !== api.defaults.baseURL) {
        api.defaults.baseURL = newBaseUrl
        console.log('✅ API地址已更新为:', newBaseUrl)
        apiInitialized = true
      }
      // 重要：更新config中的baseURL和url
      config.baseURL = api.defaults.baseURL
      // 如果url是完整URL，需要重新构建
      if (config.url && config.url.startsWith('http')) {
        const urlPath = config.url.replace(/^https?:\/\/[^/]+/, '')
        config.url = urlPath
      }
    } catch (e) {
      console.warn('⚠️ 重新检测端口失败:', e)
    }
  }

  // 计算延迟时间（指数退避）
  const delayTime = RETRY_CONFIG.retryDelay * Math.pow(RETRY_CONFIG.retryDelayMultiplier, config.__retryCount - 1)

  console.log(`🔄 请求失败，${delayTime}ms后进行第${config.__retryCount}次重试...`)
  console.log(`   使用baseURL: ${config.baseURL || api.defaults.baseURL}`)

  // 等待后重试
  await delay(delayTime)

  return api(config)
}

// 初始化：自动检测并更新API地址
let apiInitialized = false
async function initializeApi() {
  if (apiInitialized) return

  try {
    const detectedBaseUrl = await getApiBaseUrlFast()
    api.defaults.baseURL = detectedBaseUrl
    console.log('✅ API地址已初始化:', detectedBaseUrl)
    apiInitialized = true
  } catch (error) {
    console.warn('⚠️ API地址检测失败，使用默认地址:', DEFAULT_API_BASE_URL)
    api.defaults.baseURL = DEFAULT_API_BASE_URL
    apiInitialized = true
  }
}

// 立即开始初始化
initializeApi()

// 请求拦截器
api.interceptors.request.use(
  async config => {
    // 确保API已初始化
    if (!apiInitialized) {
      await initializeApi()
    }

    // 确保使用最新的baseURL（防止缓存的config使用旧的baseURL）
    if (!config.baseURL || config.baseURL === DEFAULT_API_BASE_URL) {
      config.baseURL = api.defaults.baseURL
    }

    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    // 重置重试计数（请求成功）
    if (response.config.__retryCount) {
      delete response.config.__retryCount
    }

    // 如果响应有success字段，检查是否成功
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      if (!response.data.success) {
        const message = response.data.detail || response.data.message || '请求失败'
        const error = new Error(message)
        error.response = { data: response.data }
        throw error
      }
    }
    return response.data
  },
  async error => {
    // 尝试重试
    try {
      return await retryRequest(error)
    } catch (retryError) {
      // 重试失败或不可重试，使用统一错误处理
      const enhancedError = enhanceError(retryError)
      handleError(enhancedError, { showNotification: false })
      return Promise.reject(enhancedError)
    }
  }
)

// 增强错误信息
const enhanceError = (error) => {
  if (!error.response) {
    // 网络错误
    if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      error.userMessage = '请求超时，请检查网络连接或稍后重试'
      error.errorType = 'TIMEOUT'
    } else if (error.code === 'ENOTFOUND' || error.code === 'ENETUNREACH') {
      error.userMessage = '无法连接到服务器，请检查网络连接'
      error.errorType = 'NETWORK'
    } else {
      error.userMessage = '网络错误，请检查您的网络连接'
      error.errorType = 'NETWORK'
    }
  } else {
    // HTTP错误
    const status = error.response.status
    if (status >= 500) {
      error.userMessage = '服务器错误，请稍后重试'
      error.errorType = 'SERVER'
    } else if (status === 429) {
      error.userMessage = '请求过于频繁，请稍后重试'
      error.errorType = 'RATE_LIMIT'
    } else if (status === 404) {
      error.userMessage = '请求的资源不存在'
      error.errorType = 'NOT_FOUND'
    } else if (status === 403) {
      error.userMessage = '没有权限访问该资源'
      error.errorType = 'FORBIDDEN'
    } else if (status === 401) {
      error.userMessage = '未授权，请重新登录'
      error.errorType = 'UNAUTHORIZED'
    } else if (status >= 400) {
      error.userMessage = error.response.data?.detail || error.response.data?.message || '请求参数错误'
      error.errorType = 'CLIENT'
    }
  }

  // 添加重试信息
  if (error.config?.__retryCount) {
    error.retryCount = error.config.__retryCount
    error.userMessage += ` (已重试${error.retryCount}次)`
  }

  return error
}

// API方法
export const apiService = {
  // 健康检查
  healthCheck() {
    const baseUrl = api.defaults.baseURL.replace('/api/v1', '')
    return axios.get(`${baseUrl}/health`, {
      timeout: 5000, // 健康检查使用较短超时
      __skipRetry: true // 健康检查不重试
    })
  },

  // 上传文件（使用较长超时，不自动重试）
  uploadFile(file, onProgress) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000, // 2分钟超时
      __skipRetry: true, // 文件上传不自动重试
      onUploadProgress: onProgress
    })
  },

  // 批量上传H5文件（使用较长超时，不自动重试）
  uploadH5Batch(files, onProgress) {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    return api.post('/upload-h5-batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 300000, // 5分钟超时
      __skipRetry: true, // 批量上传不自动重试
      onUploadProgress: onProgress
    })
  },

  // 获取文件列表
  getFiles() {
    return api.get('/files')
  },

  // 提取特征（使用较长超时）
  extractFeatures(data) {
    return api.post('/extract-features', data, {
      timeout: 120000 // 2分钟超时
    })
  },

  // 获取特征提取状态
  getFeatureStatus(taskId) {
    return api.get(`/features/${taskId}`)
  },

  // 训练模型（使用较长超时）
  trainModel(data) {
    return api.post('/train', data, {
      timeout: 300000 // 5分钟超时
    })
  },

  // 从H5文件训练模型（启动任务）
  trainModelFromH5(data) {
    return api.post('/train/h5', data, {
      timeout: 60000 // 1分钟超时
    })
  },

  // 查询H5训练任务状态
  getH5TrainingStatus(taskId) {
    return api.get(`/train/h5/${taskId}`)
  },

  // 从H5文件训练模型（自动识别标签）
  trainFromH5Auto(data) {
    return api.post('/train/h5/auto', data, {
      timeout: 60000 // 1分钟超时
    })
  },

  // 获取模型列表
  getModels() {
    return api.get('/models')
  },

  // 获取模型信息
  getModelInfo(modelId) {
    return api.get(`/models/${modelId}`)
  },

  // 删除模型
  deleteModel(modelId) {
    return api.delete(`/models/${modelId}`)
  },

  // 预测
  predict(data) {
    return api.post('/predict', data)
  },

  // 集成预测（使用多个模型）
  predictEnsemble(data) {
    return api.post('/predict/ensemble', data, {
      timeout: 60000 // 1分钟超时
    })
  },

  // 获取集成模型信息
  getEnsembleInfo(modelIds) {
    return api.post('/ensemble/info', { model_ids: modelIds })
  },

  // SHAP分析（已弃用，使用explainInstance或explainGlobal）
  analyzeSHAP(data) {
    return api.post('/shap/analyze', data, {
      timeout: 120000 // 2分钟超时
    })
  },

  // 获取SHAP结果（已弃用）
  getSHAPResults(modelId) {
    return api.get(`/shap/${modelId}`)
  },

  // SHAP单样本解释（局部解释）
  explainInstance(data) {
    return api.post('/shap/explain/instance', data, {
      timeout: 60000 // 1分钟超时
    })
  },

  // SHAP全局特征重要性（全局解释）
  explainGlobal(data) {
    return api.post('/shap/explain/global', data, {
      timeout: 120000 // 2分钟超时
    })
  },

  // H5文件格式检查
  checkH5Format(filePath) {
    return api.post('/h5/check-format', null, {
      params: { file_path: filePath },
      timeout: 30000
    })
  },

  // H5文件批量转换
  convertH5Files(inputFiles, outputDir = null) {
    return api.post('/h5/convert', {
      input_files: inputFiles,
      output_dir: outputDir
    }, {
      timeout: 300000 // 5分钟超时，转换可能需要较长时间
    })
  },

  // H5文件单个转换（上传并转换）
  convertSingleH5(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/h5/convert-single', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000, // 2分钟超时
      __skipRetry: true // 文件上传不自动重试
    })
  }
}

// 默认导出 apiService（已在上面通过 export const apiService 命名导出）
export default apiService

