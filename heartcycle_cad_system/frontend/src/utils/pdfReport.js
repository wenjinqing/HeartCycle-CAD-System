/**
 * PDF报告生成工具
 */
import jsPDF from 'jspdf'
import { hasMeaningfulExtendedClinical } from './clinicalDisplay'

/**
 * 生成风险评估PDF报告
 * @param {Object} options - 报告选项
 * @param {HTMLElement} options.element - 要导出的DOM元素（暂未使用）
 * @param {Object} options.data - 报告数据
 * @param {Function} options.onProgress - 进度回调
 */
export async function generatePDFReport({ element: _element, data, onProgress }) {
  try {
    if (onProgress) onProgress(10, '正在准备PDF报告...')
    
    const pdf = new jsPDF('p', 'mm', 'a4')
    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const margin = 20
    
    let yPosition = margin
    
    // 添加标题
    pdf.setFontSize(20)
    pdf.setFont('helvetica', 'bold')
    pdf.setTextColor(64, 158, 255)
    pdf.text('HeartCycle 冠心病风险评估报告', margin, yPosition)
    yPosition += 10
    
    // 添加生成时间
    pdf.setFontSize(10)
    pdf.setFont('helvetica', 'normal')
    pdf.setTextColor(100, 100, 100)
    const now = new Date()
    pdf.text(`生成时间: ${now.toLocaleString('zh-CN')}`, margin, yPosition)
    yPosition += 15
    
    // 添加分隔线
    pdf.setDrawColor(200, 200, 200)
    pdf.line(margin, yPosition, pageWidth - margin, yPosition)
    yPosition += 10
    
    // 1. 风险评估结果
    if (onProgress) onProgress(30, '正在生成风险评估结果...')
    pdf.setFontSize(16)
    pdf.setFont('helvetica', 'bold')
    pdf.setTextColor(0, 0, 0)
    pdf.text('1. 风险评估结果', margin, yPosition)
    yPosition += 10
    
    pdf.setFontSize(12)
    pdf.setFont('helvetica', 'normal')
    
    // 风险等级
    const riskLevel = data.riskLevel || '未知'
    const riskScore = data.riskScore || 0
    pdf.text(`风险等级: ${riskLevel}`, margin + 5, yPosition)
    yPosition += 7
    
    pdf.text(`风险评分: ${riskScore}%`, margin + 5, yPosition)
    yPosition += 7
    
    // 预测结果
    const prediction = data.prediction === 1 ? '高风险' : '低风险'
    pdf.text(`预测结果: ${prediction}`, margin + 5, yPosition)
    yPosition += 7
    
    // 置信度
    const confidence = data.confidence ? (data.confidence * 100).toFixed(2) : 'N/A'
    pdf.text(`预测置信度: ${confidence}%`, margin + 5, yPosition)
    yPosition += 10
    
    // 2. 预测详情
    if (onProgress) onProgress(50, '正在生成预测详情...')
    if (yPosition > pageHeight - 60) {
      pdf.addPage()
      yPosition = margin
    }
    
    pdf.setFontSize(16)
    pdf.setFont('helvetica', 'bold')
    pdf.text('2. 预测详情', margin, yPosition)
    yPosition += 10
    
    pdf.setFontSize(12)
    pdf.setFont('helvetica', 'normal')
    
    // 预测方法
    const method = data.method === 'ensemble' ? '模型集成' : '单个模型'
    pdf.text(`预测方法: ${method}`, margin + 5, yPosition)
    yPosition += 7
    
    // 概率分布
    if (data.probability && data.probability.length >= 2) {
      pdf.text(`低风险概率: ${(data.probability[0] * 100).toFixed(2)}%`, margin + 5, yPosition)
      yPosition += 7
      pdf.text(`高风险概率: ${(data.probability[1] * 100).toFixed(2)}%`, margin + 5, yPosition)
      yPosition += 10
    }
    
    // 3. 基本信息
    if (onProgress) onProgress(70, '正在生成基本信息...')
    if (yPosition > pageHeight - 60) {
      pdf.addPage()
      yPosition = margin
    }
    
    pdf.setFontSize(16)
    pdf.setFont('helvetica', 'bold')
    pdf.text('3. 基本信息', margin, yPosition)
    yPosition += 10
    
    pdf.setFontSize(12)
    pdf.setFont('helvetica', 'normal')
    
    if (data.formData) {
      const fd = data.formData
      if (fd.age) pdf.text(`年龄: ${fd.age}岁`, margin + 5, yPosition), yPosition += 7
      if (fd.gender) pdf.text(`性别: ${fd.gender === 'M' ? '男' : '女'}`, margin + 5, yPosition), yPosition += 7
      if (fd.height) pdf.text(`身高: ${fd.height}cm`, margin + 5, yPosition), yPosition += 7
      if (fd.weight) pdf.text(`体重: ${fd.weight}kg`, margin + 5, yPosition), yPosition += 7
      if (fd.bmi) pdf.text(`BMI: ${fd.bmi}`, margin + 5, yPosition), yPosition += 7
      yPosition += 5
    }

    if (data.formData && hasMeaningfulExtendedClinical(data.formData)) {
      if (yPosition > pageHeight - 80) {
        pdf.addPage()
        yPosition = margin
      }
      pdf.setFontSize(16)
      pdf.setFont('helvetica', 'bold')
      pdf.text('4. 体征与实验室', margin, yPosition)
      yPosition += 10
      pdf.setFontSize(12)
      pdf.setFont('helvetica', 'normal')
      const fd = data.formData
      const line = (t) => {
        if (yPosition > pageHeight - 20) {
          pdf.addPage()
          yPosition = margin
        }
        pdf.text(t, margin + 5, yPosition)
        yPosition += 7
      }
      if (fd.blood_pressure_systolic != null || fd.blood_pressure_diastolic != null) {
        line(`血压: ${fd.blood_pressure_systolic ?? '-'}/${fd.blood_pressure_diastolic ?? '-'} mmHg`)
      }
      if (fd.resting_heart_rate != null) line(`静息心率: ${fd.resting_heart_rate} 次/分`)
      if (fd.waist_cm != null) line(`腰围: ${fd.waist_cm} cm`)
      const yn = (v) => (v === 1 ? '是' : '否')
      if (fd.total_cholesterol != null) line(`总胆固醇: ${fd.total_cholesterol} mmol/L`)
      if (fd.ldl_cholesterol != null) line(`LDL-C: ${fd.ldl_cholesterol} mmol/L`)
      if (fd.hdl_cholesterol != null) line(`HDL-C: ${fd.hdl_cholesterol} mmol/L`)
      if (fd.triglyceride != null) line(`甘油三酯: ${fd.triglyceride} mmol/L`)
      if (fd.fasting_glucose != null) line(`空腹血糖: ${fd.fasting_glucose} mmol/L`)
      if (fd.hba1c != null) line(`HbA1c: ${fd.hba1c} %`)
      const sm = { never: '从不', former: '已戒', current: '目前吸烟' }
      if (fd.smoke_status) line(`吸烟: ${sm[fd.smoke_status] || fd.smoke_status}`)
      const act = { unknown: '不详', sedentary: '久坐少动', light: '轻度', moderate: '中度', heavy: '重度' }
      if (fd.physical_activity) line(`体力活动: ${act[fd.physical_activity] || fd.physical_activity}`)
      line(`糖尿病: ${yn(fd.diabetes)}  高血压(诊断): ${yn(fd.hypertension_dx)}  血脂异常: ${yn(fd.dyslipidemia)}`)
      line(`早发冠心病家族史: ${yn(fd.family_history_cad)}  胸痛/心绞痛: ${yn(fd.chest_pain_symptom)}`)
      yPosition += 5
    }
    
    // 5. HRV特征
    if (data.formData && (data.formData.mean_rr || data.formData.sdnn)) {
      if (yPosition > pageHeight - 80) {
        pdf.addPage()
        yPosition = margin
      }
      
      pdf.setFontSize(16)
      pdf.setFont('helvetica', 'bold')
      pdf.text('5. HRV特征', margin, yPosition)
      yPosition += 10
      
      pdf.setFontSize(12)
      pdf.setFont('helvetica', 'normal')
      
      const fd = data.formData
      // 显示所有HRV特征，如果值为null或undefined则显示N/A
      pdf.text(`平均RR间期: ${fd.mean_rr != null ? fd.mean_rr + 'ms' : 'N/A'}`, margin + 5, yPosition), yPosition += 7
      pdf.text(`SDNN: ${fd.sdnn != null ? fd.sdnn + 'ms' : 'N/A'}`, margin + 5, yPosition), yPosition += 7
      pdf.text(`RMSSD: ${fd.rmssd != null ? fd.rmssd + 'ms' : 'N/A'}`, margin + 5, yPosition), yPosition += 7
      pdf.text(`pNN50: ${fd.pnn50 != null ? fd.pnn50 + '%' : 'N/A'}`, margin + 5, yPosition), yPosition += 7
      pdf.text(`LF/HF比值: ${fd.lf_hf_ratio != null ? fd.lf_hf_ratio : 'N/A'}`, margin + 5, yPosition), yPosition += 7
      yPosition += 5
    }
    
    // 6. 健康建议
    if (onProgress) onProgress(85, '正在生成健康建议...')
    if (yPosition > pageHeight - 60) {
      pdf.addPage()
      yPosition = margin
    }
    
    pdf.setFontSize(16)
    pdf.setFont('helvetica', 'bold')
    pdf.text('6. 健康建议', margin, yPosition)
    yPosition += 10
    
    pdf.setFontSize(11)
    pdf.setFont('helvetica', 'normal')
    
    const suggestions = data.prediction === 1 ? [
      '• 及时就医，进行专业检查',
      '• 注意饮食，控制血压和血糖',
      '• 适量运动，保持健康生活方式',
      '• 定期复查，持续监测'
    ] : [
      '• 保持规律作息',
      '• 均衡饮食',
      '• 适度运动',
      '• 定期体检'
    ]
    
    suggestions.forEach(suggestion => {
      if (yPosition > pageHeight - 20) {
        pdf.addPage()
        yPosition = margin
      }
      pdf.text(suggestion, margin + 5, yPosition)
      yPosition += 7
    })
    
    // 添加页脚
    const totalPages = pdf.internal.getNumberOfPages()
    for (let i = 1; i <= totalPages; i++) {
      pdf.setPage(i)
      pdf.setFontSize(9)
      pdf.setTextColor(150, 150, 150)
      pdf.text(
        `第 ${i} 页 / 共 ${totalPages} 页`,
        pageWidth / 2,
        pageHeight - 10,
        { align: 'center' }
      )
      pdf.text(
        'HeartCycle CAD System - 仅供学术研究使用',
        pageWidth / 2,
        pageHeight - 5,
        { align: 'center' }
      )
    }
    
    if (onProgress) onProgress(100, 'PDF报告生成完成')
    
    return pdf
  } catch (error) {
    console.error('PDF生成失败:', error)
    throw error
  }
}

/**
 * 导出PDF报告
 */
export async function exportPDFReport({ element, data, filename, onProgress }) {
  try {
    const pdf = await generatePDFReport({ element, data, onProgress })
    const fileName = filename || `风险评估报告_${new Date().getTime()}.pdf`
    pdf.save(fileName)
    return true
  } catch (error) {
    console.error('导出PDF失败:', error)
    throw error
  }
}

