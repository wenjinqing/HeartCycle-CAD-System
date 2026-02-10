/**
 * SHAP分析Composable
 * 提供SHAP单样本和全局分析的统一接口
 */
import { ref, computed } from 'vue'
import { apiService } from '@/services/api'
import { handleError } from '@/utils/errorHandler'

export function useSHAPAnalysis() {
  // 状态管理
  const loading = ref(false)
  const error = ref(null)
  const instanceResult = ref(null)
  const globalResult = ref(null)

  // 计算属性
  const hasInstanceResult = computed(() => instanceResult.value !== null)
  const hasGlobalResult = computed(() => globalResult.value !== null)
  const isAnalyzing = computed(() => loading.value)

  /**
   * 单样本SHAP解释
   * @param {string} modelId - 模型ID
   * @param {Array<number>} features - 特征向量
   * @param {Object} options - 选项
   * @returns {Promise<Object>} SHAP解释结果
   */
  async function explainInstance(modelId, features, options = {}) {
    const { retry = 2, timeout = 30000 } = options

    loading.value = true
    error.value = null

    let lastError = null
    for (let attempt = 0; attempt <= retry; attempt++) {
      try {
        const result = await apiService.explainInstance({
          model_id: modelId,
          features: features
        })

        instanceResult.value = result
        loading.value = false
        return result
      } catch (err) {
        lastError = err
        if (attempt < retry) {
          // 等待后重试
          await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)))
        }
      }
    }

    // 所有重试都失败
    error.value = lastError
    loading.value = false
    handleError(lastError, {
      showNotification: true,
      context: 'SHAP单样本解释'
    })
    throw lastError
  }

  /**
   * 全局SHAP特征重要性分析
   * @param {string} modelId - 模型ID
   * @param {Object} options - 选项
   * @returns {Promise<Object>} 全局特征重要性结果
   */
  async function explainGlobal(modelId, options = {}) {
    const {
      trainingDataFile = null,
      nSamples = 100,
      retry = 2
    } = options

    loading.value = true
    error.value = null

    let lastError = null
    for (let attempt = 0; attempt <= retry; attempt++) {
      try {
        const result = await apiService.explainGlobal({
          model_id: modelId,
          training_data_file: trainingDataFile,
          n_samples: nSamples
        })

        globalResult.value = result
        loading.value = false
        return result
      } catch (err) {
        lastError = err
        if (attempt < retry) {
          await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)))
        }
      }
    }

    // 所有重试都失败
    error.value = lastError
    loading.value = false
    handleError(lastError, {
      showNotification: true,
      context: 'SHAP全局解释'
    })
    throw lastError
  }

  /**
   * 清除结果
   */
  function clearResults() {
    instanceResult.value = null
    globalResult.value = null
    error.value = null
  }

  /**
   * 清除错误
   */
  function clearError() {
    error.value = null
  }

  /**
   * 获取特征重要性排序（从全局结果）
   * @returns {Array} 排序后的特征重要性数组
   */
  const featureRanking = computed(() => {
    if (!globalResult.value || !globalResult.value.feature_ranking) {
      return []
    }
    return globalResult.value.feature_ranking
  })

  /**
   * 获取特征重要性字典（从全局结果）
   * @returns {Object} 特征重要性字典
   */
  const featureImportance = computed(() => {
    if (!globalResult.value || !globalResult.value.feature_importance) {
      return {}
    }
    return globalResult.value.feature_importance
  })

  return {
    // 状态
    loading,
    error,
    instanceResult,
    globalResult,

    // 计算属性
    hasInstanceResult,
    hasGlobalResult,
    isAnalyzing,
    featureRanking,
    featureImportance,

    // 方法
    explainInstance,
    explainGlobal,
    clearResults,
    clearError
  }
}
