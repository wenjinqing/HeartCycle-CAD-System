import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { apiService } from '../services/api'

/**
 * 模型管理 Composable
 * 提供模型列表加载、选择和管理功能
 */
export function useModelManagement() {
  const modelList = ref([])
  const loadingModels = ref(false)
  const selectedModel = ref('')
  const selectedModels = ref([])

  /**
   * 加载模型列表
   */
  const loadModelList = async () => {
    try {
      loadingModels.value = true
      const modelsResponse = await apiService.getModels()

      // 处理不同的响应格式
      let models = []
      if (modelsResponse.data && modelsResponse.data.models) {
        models = modelsResponse.data.models
      } else if (modelsResponse.models) {
        models = modelsResponse.models
      } else if (Array.isArray(modelsResponse)) {
        models = modelsResponse
      } else if (modelsResponse.data && Array.isArray(modelsResponse.data)) {
        models = modelsResponse.data
      }

      // 按创建时间排序（最新的在前）
      models.sort((a, b) => {
        const timeA = new Date(a.created_at || 0).getTime()
        const timeB = new Date(b.created_at || 0).getTime()
        return timeB - timeA
      })

      modelList.value = models

      // 如果没有选择模型且列表不为空，自动选择第一个
      if (!selectedModel.value && models.length > 0) {
        selectedModel.value = models[0].model_id
      }

      return models
    } catch (error) {
      console.error('加载模型列表失败:', error)
      ElMessage.error(`加载模型列表失败: ${error.message}`)
      modelList.value = []
      return []
    } finally {
      loadingModels.value = false
    }
  }

  /**
   * 获取模型显示名称
   */
  const getModelDisplayName = (model) => {
    let name = model.model_id || '未知模型'

    // 如果有创建时间，格式化显示
    if (model.created_at) {
      try {
        const date = new Date(model.created_at)
        const timeStr = date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
        name = `${name} (${timeStr})`
      } catch (e) {
        // 忽略日期解析错误
      }
    }

    // 如果有模型类型，添加到名称中
    if (model.model_type) {
      const typeName = getModelTypeName(model.model_type)
      name = `${name} - ${typeName}`
    }

    return name
  }

  /**
   * 获取模型类型名称
   */
  const getModelTypeName = (type) => {
    const names = {
      'lr': '逻辑回归',
      'svm': '支持向量机',
      'rf': '随机森林'
    }
    return names[type] || type
  }

  /**
   * 获取模型类型标签样式
   */
  const getModelTypeTag = (type) => {
    const tags = {
      'lr': 'primary',
      'svm': 'success',
      'rf': 'warning'
    }
    return tags[type] || 'info'
  }

  /**
   * 获取或自动选择模型ID
   */
  const getOrSelectModelId = async () => {
    if (selectedModel.value) {
      return selectedModel.value
    }

    // 如果没有选择模型，尝试加载并选择第一个
    const models = await loadModelList()
    if (!models || models.length === 0) {
      throw new Error('没有可用的模型，请先训练模型。可以在"模型训练"页面训练模型。')
    }

    return models[0].model_id
  }

  // 组件挂载时自动加载模型列表
  onMounted(() => {
    loadModelList()
  })

  return {
    modelList,
    loadingModels,
    selectedModel,
    selectedModels,
    loadModelList,
    getModelDisplayName,
    getModelTypeName,
    getModelTypeTag,
    getOrSelectModelId
  }
}
