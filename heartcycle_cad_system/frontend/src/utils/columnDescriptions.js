/**
 * 数据列名说明映射表
 * 基于HeartCycle数据集的文档说明
 */

export const columnDescriptions = {
  // 基本信息字段
  age: {
    name: 'age',
    label: '年龄',
    description: '受试者年龄（岁）',
    unit: '岁',
    required: true,
    type: 'numeric'
  },
  gender: {
    name: 'gender',
    label: '性别',
    description: '受试者性别',
    unit: 'M（男性）/ F（女性）',
    required: true,
    type: 'categorical'
  },
  height: {
    name: 'height',
    label: '身高',
    description: '受试者身高',
    unit: 'cm（厘米）',
    required: true,
    type: 'numeric'
  },
  weight: {
    name: 'weight',
    label: '体重',
    description: '受试者体重',
    unit: 'kg（千克）',
    required: true,
    type: 'numeric'
  },
  bmi: {
    name: 'bmi',
    label: 'BMI（身体质量指数）',
    description: 'Body Mass Index，由身高和体重计算得出，公式：BMI = 体重(kg) / 身高(m)²',
    unit: 'kg/m²',
    required: false,
    type: 'numeric'
  },

  // HRV特征（心率变异性特征，Heart Rate Variability）
  // 基于ECG信号提取的心率变异性指标
  mean_rr: {
    name: 'mean_rr',
    label: '平均RR间期',
    description: 'Mean RR Interval，ECG信号中连续两个R波之间的平均时间间隔',
    unit: 'ms（毫秒）',
    required: false,
    type: 'numeric',
    category: 'HRV时域特征'
  },
  sdnn: {
    name: 'sdnn',
    label: 'SDNN（正常RR间期标准差）',
    description: 'Standard Deviation of Normal-to-Normal intervals，正常RR间期的标准差，反映整体心率变异性',
    unit: 'ms（毫秒）',
    required: false,
    type: 'numeric',
    category: 'HRV时域特征'
  },
  rmssd: {
    name: 'rmssd',
    label: 'RMSSD（连续RR间期差值的均方根）',
    description: 'Root Mean Square of Successive Differences，连续RR间期差值的均方根，主要反映副交感神经活性',
    unit: 'ms（毫秒）',
    required: false,
    type: 'numeric',
    category: 'HRV时域特征'
  },
  pnn50: {
    name: 'pnn50',
    label: 'pNN50（RR间期差异超过50ms的百分比）',
    description: 'Percentage of NN intervals differing by more than 50ms，相邻RR间期差异超过50ms的百分比，反映心率变异性',
    unit: '%（百分比）',
    required: false,
    type: 'numeric',
    category: 'HRV时域特征'
  },
  lf_hf_ratio: {
    name: 'lf_hf_ratio',
    label: 'LF/HF比值（低频/高频比值）',
    description: 'Low Frequency/High Frequency Ratio，心率变异性频域分析中的低频与高频功率比值，反映自主神经系统的平衡状态',
    unit: '无量纲',
    required: false,
    type: 'numeric',
    category: 'HRV频域特征'
  }
}

/**
 * 获取列名的完整描述信息
 * @param {string} columnName - 列名
 * @returns {Object|null} 列的描述信息对象
 */
export function getColumnDescription(columnName) {
  return columnDescriptions[columnName] || null
}

/**
 * 获取列名的中文标签
 * @param {string} columnName - 列名
 * @returns {string} 中文标签，如果不存在则返回原列名
 */
export function getColumnLabel(columnName) {
  const desc = getColumnDescription(columnName)
  return desc ? desc.label : columnName
}

/**
 * 获取列名的详细说明
 * @param {string} columnName - 列名
 * @returns {string} 详细说明，如果不存在则返回空字符串
 */
export function getColumnDescriptionText(columnName) {
  const desc = getColumnDescription(columnName)
  if (!desc) return ''
  let text = desc.description
  if (desc.unit) {
    text += `，单位：${desc.unit}`
  }
  if (desc.category) {
    text += `（${desc.category}）`
  }
  return text
}

/**
 * 获取所有必需列的列表
 * @returns {Array} 必需列的数组
 */
export function getRequiredColumns() {
  return Object.values(columnDescriptions)
    .filter(col => col.required)
    .map(col => col.name)
}

/**
 * 获取所有可选列的列表
 * @returns {Array} 可选列的数组
 */
export function getOptionalColumns() {
  return Object.values(columnDescriptions)
    .filter(col => !col.required)
    .map(col => col.name)
}

/**
 * 按类别分组列名
 * @returns {Object} 按类别分组的列名对象
 */
export function getColumnsByCategory() {
  const categories = {}
  Object.values(columnDescriptions).forEach(col => {
    const category = col.category || '基本信息'
    if (!categories[category]) {
      categories[category] = []
    }
    categories[category].push(col)
  })
  return categories
}

