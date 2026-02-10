/**
 * 特征名称到中文解释的映射
 * 用于全局特征重要性展示
 */
export const featureDescriptions = {
  // HRV时域特征
  'mean_rr': '平均RR间期',
  'std_rr': 'RR间期标准差',
  'min_rr': '最小RR间期',
  'max_rr': '最大RR间期',
  'median_rr': 'RR间期中位数',
  'sdnn': 'RR间期标准差（SDNN）',
  'rmssd': '相邻RR间期差值的均方根（RMSSD）',
  'pnn50': '相邻RR间期差异超过50ms的百分比',
  'sdsd': '相邻RR间期差值的标准差（SDSD）',
  'hrv_triangular_index': '心率变异性三角指数',
  'tinn': 'RR间期直方图三角插值（TINN）',
  'mean_hr': '平均心率',
  
  // HRV频域特征
  'total_power': '总功率',
  'vlf_power': '极低频功率',
  'lf_power': '低频功率',
  'hf_power': '高频功率',
  'lf_hf_ratio': '低频与高频功率比值',
  'lf_norm': '归一化低频功率',
  'hf_norm': '归一化高频功率',
  'vlf_percent': '极低频功率百分比',
  'lf_percent': '低频功率百分比',
  'hf_percent': '高频功率百分比',
  
  // HRV非线性特征
  'sd1': 'Poincaré图短轴标准差（SD1）',
  'sd2': 'Poincaré图长轴标准差（SD2）',
  'sd1_sd2_ratio': 'SD1与SD2比值',
  'sample_entropy': '样本熵',
  'approximate_entropy': '近似熵',
  
  // 临床特征
  'age': '年龄',
  'gender': '性别',
  'height': '身高',
  'weight': '体重',
  'bmi': '体重指数（BMI）'
}

/**
 * 获取特征的中文解释
 * @param {string} featureName - 特征名称
 * @returns {string} 中文解释，如果不存在则返回原名称
 */
export function getFeatureDescription(featureName) {
  return featureDescriptions[featureName] || featureName
}

/**
 * 获取特征的详细说明
 * @param {string} featureName - 特征名称
 * @returns {string} 详细说明
 */
export function getFeatureDetail(featureName) {
  const details = {
    'mean_rr': '反映心率的平均水平，单位：毫秒（ms）',
    'std_rr': '反映RR间期的变异性，单位：毫秒（ms）',
    'min_rr': '最短的RR间期，单位：毫秒（ms）',
    'max_rr': '最长的RR间期，单位：毫秒（ms）',
    'median_rr': 'RR间期的中位数，单位：毫秒（ms）',
    'sdnn': '所有RR间期的标准差，反映整体心率变异性，单位：毫秒（ms）',
    'rmssd': '相邻RR间期差值的均方根，反映短期心率变异性，单位：毫秒（ms）',
    'pnn50': '相邻RR间期差异超过50ms的百分比，反映心率变异性，单位：%（百分比）',
    'sdsd': '相邻RR间期差值的标准差，单位：毫秒（ms）',
    'hrv_triangular_index': '心率变异性三角指数，反映整体心率变异性',
    'tinn': 'RR间期直方图三角插值，反映心率变异性',
    'mean_hr': '平均心率，单位：次/分钟（bpm）',
    'total_power': '频域分析的总功率，反映整体心率变异性',
    'vlf_power': '极低频功率（0.0033-0.04 Hz），反映长期调节机制',
    'lf_power': '低频功率（0.04-0.15 Hz），反映交感神经活动',
    'hf_power': '高频功率（0.15-0.4 Hz），反映副交感神经活动',
    'lf_hf_ratio': '低频与高频功率比值，反映自主神经系统平衡状态',
    'lf_norm': '归一化低频功率，无量纲',
    'hf_norm': '归一化高频功率，无量纲',
    'vlf_percent': '极低频功率占总功率的百分比',
    'lf_percent': '低频功率占总功率的百分比',
    'hf_percent': '高频功率占总功率的百分比',
    'sd1': 'Poincaré图短轴标准差，反映短期心率变异性',
    'sd2': 'Poincaré图长轴标准差，反映长期心率变异性',
    'sd1_sd2_ratio': 'SD1与SD2比值，反映心率变异性的短期与长期关系',
    'sample_entropy': '样本熵，反映心率序列的复杂度和规律性',
    'approximate_entropy': '近似熵，反映心率序列的复杂度和可预测性',
    'age': '年龄，单位：岁',
    'gender': '性别（M=男性，F=女性）',
    'height': '身高，单位：厘米（cm）',
    'weight': '体重，单位：千克（kg）',
    'bmi': '体重指数，计算公式：体重(kg) / 身高(m)²'
  }
  return details[featureName] || '暂无详细说明'
}

