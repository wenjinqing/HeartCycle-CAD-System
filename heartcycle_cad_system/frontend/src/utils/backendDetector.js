/**
 * 后端端口自动检测工具
 * 自动查找可用的后端服务端口
 */

// 保存当前工作的端口
let currentWorkingPort = null

/**
 * 检测指定端口的后端服务是否可用
 * @param {number} port - 端口号
 * @returns {Promise<boolean>} - 是否可用
 */
async function checkBackendPort(port) {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 3000) // 增加超时时间到3秒

    const response = await fetch(`http://localhost:${port}/health`, {
      method: 'GET',
      signal: controller.signal,
      cache: 'no-cache' // 禁用缓存
    })

    clearTimeout(timeoutId)

    if (response.ok) {
      const data = await response.json()
      // 验证是否是我们的后端服务
      if (data.version && data.status) {
        console.log(`✅ 端口 ${port} 验证成功:`, data)
        currentWorkingPort = port
        return true
      } else {
        console.log(`⚠️ 端口 ${port} 响应格式不正确:`, data)
      }
    } else {
      console.log(`⚠️ 端口 ${port} 响应状态码: ${response.status}`)
    }
    return false
  } catch (error) {
    // 只在非超时错误时记录详细信息
    if (error.name !== 'AbortError') {
      console.log(`⚠️ 端口 ${port} 检测失败: ${error.message}`)
    }
    return false
  }
}

/**
 * 自动检测后端服务端口
 * @param {number} startPort - 起始端口（默认8000）
 * @param {number} maxAttempts - 最大尝试次数（默认10）
 * @returns {Promise<number|null>} - 找到的端口号，未找到返回null
 */
export async function detectBackendPort(startPort = 8000, maxAttempts = 10) {
  console.log('🔍 正在检测后端服务端口...')

  for (let port = startPort; port < startPort + maxAttempts; port++) {
    console.log(`  检测端口 ${port}...`)

    if (await checkBackendPort(port)) {
      console.log(`✅ 找到后端服务: http://localhost:${port}`)
      // 保存到localStorage
      localStorage.setItem('lastWorkingPort', port.toString())
      return port
    }
  }

  console.error(`❌ 未找到后端服务 (尝试了端口 ${startPort}-${startPort + maxAttempts - 1})`)
  return null
}

/**
 * 获取后端API基础URL
 * 优先使用环境变量，如果未设置则自动检测
 * @returns {Promise<string>} - API基础URL
 */
export async function getApiBaseUrl() {
  // 优先使用环境变量配置
  if (process.env.VUE_APP_API_BASE_URL) {
    console.log('📌 使用配置的API地址:', process.env.VUE_APP_API_BASE_URL)
    return process.env.VUE_APP_API_BASE_URL
  }

  // 自动检测端口
  const port = await detectBackendPort()

  if (port) {
    const baseUrl = `http://localhost:${port}/api/v1`
    console.log('🎯 自动检测到API地址:', baseUrl)
    return baseUrl
  }

  // 检测失败，使用默认值
  console.warn('⚠️ 使用默认API地址: http://localhost:8000/api/v1')
  return 'http://localhost:8000/api/v1'
}

/**
 * 从localStorage获取上次检测到的端口
 * @returns {number|null} - 端口号
 */
export function getLastDetectedPort() {
  const port = localStorage.getItem('lastWorkingPort')
  return port ? parseInt(port, 10) : null
}

/**
 * 快速检测（优先使用上次的端口）
 * @returns {Promise<string>} - API基础URL
 */
export async function getApiBaseUrlFast() {
  // 优先使用环境变量
  if (process.env.VUE_APP_API_BASE_URL) {
    return process.env.VUE_APP_API_BASE_URL
  }

  // 尝试上次检测到的端口
  const lastPort = getLastDetectedPort()
  if (lastPort) {
    console.log(`🔄 尝试上次的端口 ${lastPort}...`)
    if (await checkBackendPort(lastPort)) {
      console.log(`✅ 端口 ${lastPort} 仍然可用`)
      return `http://localhost:${lastPort}/api/v1`
    }
    console.log(`⚠️ 端口 ${lastPort} 不可用，重新检测...`)
    // 清除无效的缓存
    localStorage.removeItem('lastWorkingPort')
  }

  // 重新检测
  return await getApiBaseUrl()
}

/**
 * 获取当前工作的端口
 * @returns {number|null}
 */
export function getCurrentWorkingPort() {
  return currentWorkingPort || getLastDetectedPort()
}

export default {
  detectBackendPort,
  getApiBaseUrl,
  getApiBaseUrlFast,
  checkBackendPort,
  getLastDetectedPort,
  getCurrentWorkingPort
}
