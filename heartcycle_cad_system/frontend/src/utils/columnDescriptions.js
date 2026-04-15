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
  },

  blood_pressure_systolic: {
    name: 'blood_pressure_systolic',
    label: '收缩压',
    description: '收缩压',
    unit: 'mmHg',
    required: false,
    type: 'numeric',
    category: '体征与危险因素'
  },
  blood_pressure_diastolic: {
    name: 'blood_pressure_diastolic',
    label: '舒张压',
    description: '舒张压',
    unit: 'mmHg',
    required: false,
    type: 'numeric',
    category: '体征与危险因素'
  },
  resting_heart_rate: {
    name: 'resting_heart_rate',
    label: '静息心率',
    description: '静息心率',
    unit: '次/分',
    required: false,
    type: 'numeric',
    category: '体征与危险因素'
  },
  waist_cm: {
    name: 'waist_cm',
    label: '腰围',
    description: '腰围',
    unit: 'cm',
    required: false,
    type: 'numeric',
    category: '体征与危险因素'
  },
  total_cholesterol: {
    name: 'total_cholesterol',
    label: '总胆固醇',
    description: '总胆固醇',
    unit: 'mmol/L',
    required: false,
    type: 'numeric',
    category: '实验室'
  },
  ldl_cholesterol: {
    name: 'ldl_cholesterol',
    label: 'LDL-C',
    description: '低密度脂蛋白胆固醇',
    unit: 'mmol/L',
    required: false,
    type: 'numeric',
    category: '实验室'
  },
  hdl_cholesterol: {
    name: 'hdl_cholesterol',
    label: 'HDL-C',
    description: '高密度脂蛋白胆固醇',
    unit: 'mmol/L',
    required: false,
    type: 'numeric',
    category: '实验室'
  },
  triglyceride: {
    name: 'triglyceride',
    label: '甘油三酯',
    description: '甘油三酯',
    unit: 'mmol/L',
    required: false,
    type: 'numeric',
    category: '实验室'
  },
  fasting_glucose: {
    name: 'fasting_glucose',
    label: '空腹血糖',
    description: '空腹血糖',
    unit: 'mmol/L',
    required: false,
    type: 'numeric',
    category: '实验室'
  },
  hba1c: {
    name: 'hba1c',
    label: 'HbA1c',
    description: '糖化血红蛋白',
    unit: '%',
    required: false,
    type: 'numeric',
    category: '实验室'
  },
  smoke_status: {
    name: 'smoke_status',
    label: '吸烟',
    description: '吸烟状态',
    unit: 'never/former/current',
    required: false,
    type: 'categorical',
    category: '生活方式'
  },
  physical_activity: {
    name: 'physical_activity',
    label: '体力活动',
    description: '体力活动水平',
    unit: '',
    required: false,
    type: 'categorical',
    category: '生活方式'
  },
  diabetes: {
    name: 'diabetes',
    label: '糖尿病',
    description: '糖尿病史',
    unit: '0/1',
    required: false,
    type: 'numeric',
    category: '危险因素'
  },
  hypertension_dx: {
    name: 'hypertension_dx',
    label: '高血压(诊断)',
    description: '临床诊断高血压',
    unit: '0/1',
    required: false,
    type: 'numeric',
    category: '危险因素'
  },
  dyslipidemia: {
    name: 'dyslipidemia',
    label: '血脂异常',
    description: '血脂异常',
    unit: '0/1',
    required: false,
    type: 'numeric',
    category: '危险因素'
  },
  family_history_cad: {
    name: 'family_history_cad',
    label: '早发冠心病家族史',
    description: '早发冠心病家族史',
    unit: '0/1',
    required: false,
    type: 'numeric',
    category: '危险因素'
  },
  chest_pain_symptom: {
    name: 'chest_pain_symptom',
    label: '胸痛/心绞痛症状',
    description: '胸痛或心绞痛症状',
    unit: '0/1',
    required: false,
    type: 'numeric',
    category: '危险因素'
  },
  patient_id: {
    name: 'patient_id',
    label: '患者标识',
    description: 'CSV 中的患者编号或标识',
    required: false,
    type: 'string',
    category: '标识'
  },
  name: {
    name: 'name',
    label: '姓名',
    description: '姓名',
    required: false,
    type: 'string',
    category: '标识'
  },
  prediction: {
    name: 'prediction',
    label: '预测类别',
    description: '模型输出的类别标签',
    unit: '0/1',
    required: false,
    type: 'numeric',
    category: '预测结果'
  },
  confidence: {
    name: 'confidence',
    label: '置信度',
    description: '预测置信度',
    unit: '0–1',
    required: false,
    type: 'numeric',
    category: '预测结果'
  },
  riskScore: {
    name: 'riskScore',
    label: '风险评分',
    description: '由正类概率换算的百分比',
    unit: '%',
    required: false,
    type: 'numeric',
    category: '预测结果'
  },
  probability: {
    name: 'probability',
    label: '类别概率',
    description: '各类别预测概率向量',
    required: false,
    type: 'string',
    category: '预测结果'
  },
  error: {
    name: 'error',
    label: '错误信息',
    description: '该行预测失败时的错误说明',
    required: false,
    type: 'string',
    category: '预测结果'
  }
}

/** CSV 列名别名 → canonical key（与 clinicalFeatureVector 一致） */
export const columnLabelAliases = {
  bp_sys: 'blood_pressure_systolic',
  bp_dia: 'blood_pressure_diastolic',
  resting_hr: 'resting_heart_rate',
  tc: 'total_cholesterol',
  ldl: 'ldl_cholesterol',
  hdl: 'hdl_cholesterol',
  tg: 'triglyceride',
  fpg: 'fasting_glucose',
  hypertension: 'hypertension_dx'
}

/**
 * 获取列名的完整描述信息
 * @param {string} columnName - 列名
 * @returns {Object|null} 列的描述信息对象
 */
function resolveColumnKey (columnName) {
  return columnLabelAliases[columnName] || columnName
}

export function getColumnDescription (columnName) {
  return columnDescriptions[resolveColumnKey(columnName)] || null
}

/**
 * 获取列名的中文标签
 * @param {string} columnName - 列名
 * @returns {string} 中文标签，如果不存在则返回原列名
 */
export function getColumnLabel (columnName) {
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

