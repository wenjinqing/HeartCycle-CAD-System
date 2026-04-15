/**
 * 扩展临床指标：展示文案与「是否有有效填写」判断（监测表单、历史记录、PDF 共用）
 */

export function smokeLabel (v) {
  return (
    { never: '从不吸烟', former: '已戒烟', current: '目前吸烟' }[v] || (v ? String(v) : '—')
  )
}

export function activityLabel (v) {
  return (
    {
      unknown: '不详',
      sedentary: '久坐少动',
      light: '轻度活动',
      moderate: '中度活动',
      heavy: '重度活动'
    }[v] || (v ? String(v) : '—')
  )
}

export function yesNoFlag (n) {
  if (n === 1 || n === '1' || n === true) return '是'
  if (n === 0 || n === '0' || n === false) return '否'
  return '—'
}

export function labFmt (val, unit) {
  return val != null && val !== '' ? `${Number(val)} ${unit}` : '—'
}

/** 是否与默认空表单有区别，用于展示扩展区块 / PDF 小节 */
export function hasMeaningfulExtendedClinical (fd) {
  if (!fd) return false
  if (fd.blood_pressure_systolic != null || fd.blood_pressure_diastolic != null) return true
  if (fd.resting_heart_rate != null) return true
  if (fd.waist_cm != null) return true
  if (
    [fd.total_cholesterol, fd.ldl_cholesterol, fd.hdl_cholesterol, fd.triglyceride, fd.fasting_glucose, fd.hba1c].some(
      (x) => x != null && x !== ''
    )
  ) {
    return true
  }
  if (fd.smoke_status && fd.smoke_status !== 'never') return true
  if (fd.physical_activity && fd.physical_activity !== 'unknown') return true
  const riskOn = (x) => x === 1 || x === '1' || x === true
  if (
    riskOn(fd.diabetes) ||
    riskOn(fd.hypertension_dx) ||
    riskOn(fd.dyslipidemia) ||
    riskOn(fd.family_history_cad) ||
    riskOn(fd.chest_pain_symptom)
  ) {
    return true
  }
  return false
}
