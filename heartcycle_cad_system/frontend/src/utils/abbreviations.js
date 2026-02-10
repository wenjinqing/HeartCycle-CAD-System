/**
 * 缩写词中文解释映射
 * 用于在UI中为缩写添加中文解释
 */

export const abbreviations = {
  // 医学术语
  HRV: {
    full: 'Heart Rate Variability',
    chinese: '心率变异性',
    description: '心率变异性，反映自主神经系统的功能状态'
  },
  ECG: {
    full: 'Electrocardiogram',
    chinese: '心电图',
    description: '心电图，记录心脏电活动的图形'
  },
  HDF5: {
    full: 'Hierarchical Data Format 5',
    chinese: '分层数据格式5',
    description: '分层数据格式5，用于存储和组织大量数据的文件格式'
  },
  H5: {
    full: 'HDF5',
    chinese: 'HDF5格式',
    description: 'HDF5格式文件的简称'
  },
  CAD: {
    full: 'Coronary Artery Disease',
    chinese: '冠心病',
    description: '冠心病，冠状动脉疾病'
  },
  BMI: {
    full: 'Body Mass Index',
    chinese: '身体质量指数',
    description: '身体质量指数，用于评估体重与身高的比例'
  },
  
  // 机器学习相关
  SHAP: {
    full: 'SHapley Additive exPlanations',
    chinese: 'SHAP可解释性分析',
    description: 'SHAP值，用于解释机器学习模型预测结果的特征贡献度'
  },
  RF: {
    full: 'Random Forest',
    chinese: '随机森林',
    description: '随机森林，一种集成学习算法'
  },
  SVM: {
    full: 'Support Vector Machine',
    chinese: '支持向量机',
    description: '支持向量机，一种监督学习算法'
  },
  LR: {
    full: 'Logistic Regression',
    chinese: '逻辑回归',
    description: '逻辑回归，一种用于分类的线性模型'
  },
  AUC: {
    full: 'Area Under Curve',
    chinese: '曲线下面积',
    description: 'ROC曲线下面积，用于评估分类模型性能'
  },
  ROC: {
    full: 'Receiver Operating Characteristic',
    chinese: '受试者工作特征曲线',
    description: 'ROC曲线，用于评估二分类模型性能'
  },
  F1: {
    full: 'F1 Score',
    chinese: 'F1分数',
    description: 'F1分数，精确率和召回率的调和平均数'
  },
  
  // HRV特征
  SDNN: {
    full: 'Standard Deviation of Normal-to-Normal intervals',
    chinese: '正常RR间期标准差',
    description: '正常RR间期的标准差，反映整体心率变异性'
  },
  RMSSD: {
    full: 'Root Mean Square of Successive Differences',
    chinese: '连续RR间期差值的均方根',
    description: '连续RR间期差值的均方根，主要反映副交感神经活性'
  },
  pNN50: {
    full: 'Percentage of NN intervals differing by more than 50ms',
    chinese: '相邻RR间期差异超过50ms的百分比',
    description: '相邻RR间期差异超过50ms的百分比，反映心率变异性'
  },
  'LF/HF': {
    full: 'Low Frequency/High Frequency Ratio',
    chinese: '低频与高频功率比值',
    description: '心率变异性频域分析中的低频与高频功率比值，反映自主神经系统的平衡状态'
  },
  
  // 技术术语
  CSV: {
    full: 'Comma-Separated Values',
    chinese: '逗号分隔值',
    description: '逗号分隔值文件格式，用于存储表格数据'
  },
  PDF: {
    full: 'Portable Document Format',
    chinese: '便携式文档格式',
    description: '便携式文档格式，用于文档交换'
  },
  JSON: {
    full: 'JavaScript Object Notation',
    chinese: 'JavaScript对象表示法',
    description: 'JavaScript对象表示法，一种轻量级数据交换格式'
  },
  API: {
    full: 'Application Programming Interface',
    chinese: '应用程序接口',
    description: '应用程序接口，用于不同软件组件之间的通信'
  },
  UUID: {
    full: 'Universally Unique Identifier',
    chinese: '通用唯一标识符',
    description: '通用唯一标识符，用于唯一标识信息'
  }
}

/**
 * 获取缩写的中文解释
 * @param {string} abbr - 缩写词
 * @returns {string} 中文解释，格式：缩写（中文全称）
 */
export function getAbbreviationExplanation(abbr) {
  if (!abbr) return abbr
  
  const abbrUpper = abbr.toUpperCase()
  const info = abbreviations[abbrUpper] || abbreviations[abbr]
  
  if (info) {
    return `${abbr}（${info.chinese}）`
  }
  
  return abbr
}

/**
 * 获取缩写的完整信息
 * @param {string} abbr - 缩写词
 * @returns {Object|null} 包含full、chinese、description的对象
 */
export function getAbbreviationInfo(abbr) {
  if (!abbr) return null
  
  const abbrUpper = abbr.toUpperCase()
  return abbreviations[abbrUpper] || abbreviations[abbr] || null
}

/**
 * 格式化标签，添加中文解释
 * @param {string} label - 原始标签
 * @param {string} abbr - 缩写词（可选，如果label中包含缩写）
 * @returns {string} 格式化后的标签
 */
export function formatLabelWithAbbr(label, abbr = null) {
  if (!label) return label
  
  // 如果没有指定缩写，尝试从标签中提取
  if (!abbr) {
    // 检查常见缩写模式
    const abbrPatterns = [
      /\bHRV\b/i,
      /\bECG\b/i,
      /\bHDF5\b/i,
      /\bH5\b/i,
      /\bSHAP\b/i,
      /\bRF\b/i,
      /\bSVM\b/i,
      /\bLR\b/i,
      /\bAUC\b/i,
      /\bROC\b/i,
      /\bF1\b/i,
      /\bSDNN\b/i,
      /\bRMSSD\b/i,
      /\bpNN50\b/i,
      /\bLF\/HF\b/i,
      /\bBMI\b/i,
      /\bCAD\b/i,
      /\bCSV\b/i,
      /\bPDF\b/i,
      /\bJSON\b/i,
      /\bAPI\b/i,
      /\bUUID\b/i
    ]
    
    for (const pattern of abbrPatterns) {
      const match = label.match(pattern)
      if (match) {
        abbr = match[0]
        break
      }
    }
  }
  
  if (abbr) {
    const info = getAbbreviationInfo(abbr)
    if (info) {
      // 替换标签中的缩写为"缩写（中文）"
      return label.replace(new RegExp(`\\b${abbr}\\b`, 'gi'), `${abbr}（${info.chinese}）`)
    }
  }
  
  return label
}

/**
 * 获取工具提示内容（包含完整解释）
 * @param {string} abbr - 缩写词
 * @returns {string} 工具提示内容
 */
export function getAbbreviationTooltip(abbr) {
  if (!abbr) return ''
  
  const info = getAbbreviationInfo(abbr)
  if (info) {
    return `${info.full}：${info.chinese}。${info.description}`
  }
  
  return ''
}

