/**
 * 统一错误处理工具
 */
import { ElMessage, ElNotification } from 'element-plus'

/**
 * 错误码映射
 */
const ERROR_MESSAGES = {
  // 通用错误
  INTERNAL_SERVER_ERROR: '服务器内部错误，请稍后重试',
  INVALID_REQUEST: '请求参数无效',
  VALIDATION_ERROR: '数据验证失败',
  NOT_FOUND: '资源未找到',
  
  // 文件相关
  FILE_NOT_FOUND: '文件未找到',
  FILE_UPLOAD_FAILED: '文件上传失败',
  FILE_TYPE_NOT_SUPPORTED: '不支持的文件类型',
  FILE_TOO_LARGE: '文件过大，请选择较小的文件',
  
  // 特征提取
  FEATURE_EXTRACTION_FAILED: '特征提取失败',
  FEATURE_EXTRACTION_TIMEOUT: '特征提取超时',
  INSUFFICIENT_DATA: '数据不足，无法提取特征',
  
  // 模型训练
  MODEL_TRAINING_FAILED: '模型训练失败',
  MODEL_NOT_FOUND: '模型未找到',
  INSUFFICIENT_SAMPLES: '样本数量不足',
  INVALID_LABELS: '标签数据无效',
  
  // 预测
  PREDICTION_FAILED: '预测失败',
  INVALID_FEATURES: '特征数据无效',
  FEATURE_MISMATCH: '特征数量不匹配',
  
  // 任务
  TASK_NOT_FOUND: '任务未找到',
  TASK_ALREADY_COMPLETED: '任务已完成',
  TASK_FAILED: '任务执行失败',
  
  // 参数
  INVALID_PARAMETER: '参数错误',
  MISSING_REQUIRED_PARAMETER: '缺少必需参数',
  PARAMETER_OUT_OF_RANGE: '参数超出范围'
}

/**
 * 处理API错误
 * @param {Error} error - 错误对象
 * @param {Object} options - 选项
 * @param {boolean} options.showNotification - 是否显示通知（默认false）
 * @param {string} options.defaultMessage - 默认错误消息
 * @returns {string} 错误消息
 */
export function handleError(error, options = {}) {
  const {
    showNotification = false,
    defaultMessage = '操作失败，请稍后重试'
  } = options
  
  let message = defaultMessage
  let errorCode = null
  
  // 从错误对象中提取信息
  if (error.response) {
    // API返回的错误
    const data = error.response.data
    if (data) {
      errorCode = data.error_code
      message = data.detail || data.message || ERROR_MESSAGES[errorCode] || message
    } else {
      message = `HTTP ${error.response.status}: ${error.response.statusText}`
    }
  } else if (error.request) {
    // 网络错误
    message = '网络连接失败，请检查网络或后端服务是否启动'
  } else if (error.message) {
    // 其他错误
    message = error.message
  }
  
  // 显示错误提示
  if (showNotification) {
    ElNotification({
      title: '错误',
      message: message,
      type: 'error',
      duration: 5000
    })
  } else {
    ElMessage.error(message)
  }
  
  // 记录错误日志
  console.error('Error:', {
    errorCode,
    message,
    error: error.response?.data || error.message
  })
  
  return message
}

/**
 * 处理网络错误
 */
export function handleNetworkError() {
  ElMessage.error('网络连接失败，请检查网络或后端服务是否启动')
}

/**
 * 处理验证错误
 */
export function handleValidationError(errors) {
  const messages = errors.map(err => {
    const field = err.field || err.loc?.join('.') || '未知字段'
    return `${field}: ${err.msg || err.message}`
  }).join('; ')
  
  ElMessage.error(`数据验证失败: ${messages}`)
  return messages
}

/**
 * 错误重试装饰器
 * @param {Function} fn - 要重试的函数
 * @param {number} maxRetries - 最大重试次数
 * @param {number} delay - 重试延迟（毫秒）
 */
export function withRetry(fn, maxRetries = 3, delay = 1000) {
  return async function(...args) {
    let lastError
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await fn(...args)
      } catch (error) {
        lastError = error
        if (i < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, delay * (i + 1)))
        }
      }
    }
    throw lastError
  }
}

export default {
  handleError,
  handleNetworkError,
  handleValidationError,
  withRetry
}

