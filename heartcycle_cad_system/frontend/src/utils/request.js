/**
 * 请求工具函数
 */
import axios from 'axios'
import { ElMessage, ElLoading } from 'element-plus'

// 创建axios实例
const service = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 可以在这里添加token等
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  error => {
    console.error('Request Error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    const res = response.data
    
    // 如果响应有success字段，检查是否成功
    if (res && typeof res === 'object' && 'success' in res) {
      if (!res.success) {
        const message = res.detail || res.message || '请求失败'
        ElMessage.error(message)
        return Promise.reject(new Error(message))
      }
      // 返回data字段（如果有）
      return res.data !== undefined ? res.data : res
    }
    
    return res
  },
  error => {
    let message = '请求失败'
    
    if (error.response) {
      const data = error.response.data
      if (data) {
        if (typeof data === 'object') {
          message = data.detail || data.message || data.error || message
        } else {
          message = data
        }
      } else {
        message = `HTTP ${error.response.status}: ${error.response.statusText}`
      }
    } else if (error.request) {
      message = '网络错误，请检查网络连接或后端服务是否启动'
    } else {
      message = error.message || message
    }
    
    ElMessage.error(message)
    console.error('Response Error:', error)
    return Promise.reject(error)
  }
)

export default service


