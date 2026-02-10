/**
 * 加载状态管理
 */
import { ElLoading } from 'element-plus'

let loadingInstance = null

/**
 * 显示全屏加载
 * @param {string} text - 加载文本
 * @param {Object} options - 选项
 */
export function showLoading(text = '加载中...', options = {}) {
  if (loadingInstance) {
    loadingInstance.setText(text)
    return loadingInstance
  }
  
  loadingInstance = ElLoading.service({
    lock: true,
    text: text,
    background: 'rgba(0, 0, 0, 0.7)',
    ...options
  })
  
  return loadingInstance
}

/**
 * 隐藏加载
 */
export function hideLoading() {
  if (loadingInstance) {
    loadingInstance.close()
    loadingInstance = null
  }
}

/**
 * 加载装饰器
 * @param {Function} fn - 要包装的函数
 * @param {string} loadingText - 加载文本
 */
export function withLoading(fn, loadingText = '加载中...') {
  return async function(...args) {
    const loading = showLoading(loadingText)
    try {
      const result = await fn(...args)
      return result
    } finally {
      hideLoading()
    }
  }
}

/**
 * 按钮加载状态管理
 */
export class ButtonLoading {
  constructor(buttonRef) {
    this.buttonRef = buttonRef
    this.originalText = null
  }
  
  start(text = '处理中...') {
    if (this.buttonRef && this.buttonRef.value) {
      this.originalText = this.buttonRef.value.textContent || this.buttonRef.value.innerText
      this.buttonRef.value.disabled = true
      this.buttonRef.value.loading = true
      if (text) {
        this.buttonRef.value.textContent = text
      }
    }
  }
  
  stop() {
    if (this.buttonRef && this.buttonRef.value) {
      this.buttonRef.value.disabled = false
      this.buttonRef.value.loading = false
      if (this.originalText) {
        this.buttonRef.value.textContent = this.originalText
      }
    }
  }
}

export default {
  showLoading,
  hideLoading,
  withLoading,
  ButtonLoading
}

