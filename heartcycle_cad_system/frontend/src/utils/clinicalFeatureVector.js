/**
 * 与监测页、批量预测一致：在基础特征后追加扩展临床维度（顺序需与训练数据一致）。
 * 旧模型通常只读前 10 维；新模型可读全长。
 */

export function appendExtendedClinicalFeaturesFromForm (features, fd) {
  if (!fd) return
  const num = (v) => {
    if (v === null || v === undefined || v === '') return 0
    const x = Number(v)
    return Number.isFinite(x) ? x : 0
  }
  const b01 = (v) => (v === 1 || v === true ? 1 : 0)
  const smokeMap = { never: 0, former: 1, current: 2, unknown: 0, '': 0 }
  const actMap = { unknown: 0, sedentary: 0, light: 1, moderate: 2, heavy: 3, '': 0 }
  features.push(num(fd.blood_pressure_systolic))
  features.push(num(fd.blood_pressure_diastolic))
  features.push(num(fd.resting_heart_rate))
  features.push(num(fd.waist_cm))
  features.push(num(fd.total_cholesterol))
  features.push(num(fd.ldl_cholesterol))
  features.push(num(fd.hdl_cholesterol))
  features.push(num(fd.triglyceride))
  features.push(num(fd.fasting_glucose))
  features.push(num(fd.hba1c))
  features.push(smokeMap[fd.smoke_status] ?? 0)
  features.push(b01(fd.diabetes))
  features.push(b01(fd.hypertension_dx))
  features.push(b01(fd.dyslipidemia))
  features.push(b01(fd.family_history_cad))
  features.push(b01(fd.chest_pain_symptom))
  features.push(actMap[fd.physical_activity] ?? 0)
}

/** CSV 行 -> 与 formData 同结构的扩展字段（缺失则默认） */
export function extendedFieldsFromCsvRow (row) {
  const g = (k) => (row && row[k] !== undefined && row[k] !== null ? String(row[k]).trim() : '')
  const num = (k) => {
    const v = g(k)
    if (v === '') return null
    const x = parseFloat(v)
    return Number.isFinite(x) ? x : null
  }
  const bin = (k) => {
    const v = g(k).toLowerCase()
    if (v === '1' || v === 'true' || v === 'yes' || v === 'y') return 1
    if (v === '0' || v === 'false' || v === 'no' || v === 'n' || v === '') return 0
    return 0
  }
  const smoke = g('smoke_status') || 'never'
  const act = g('physical_activity') || 'unknown'
  const smokeNum = parseInt(g('smoking_status'), 10)
  const smokeFromNumeric = Number.isFinite(smokeNum)
    ? (smokeNum >= 2 ? 'current' : smokeNum === 1 ? 'former' : 'never')
    : null
  return {
    blood_pressure_systolic: num('blood_pressure_systolic') ?? num('bp_sys') ?? num('sbp'),
    blood_pressure_diastolic: num('blood_pressure_diastolic') ?? num('bp_dia') ?? num('dbp'),
    resting_heart_rate: num('resting_heart_rate') ?? num('resting_hr') ?? num('heart_rate'),
    waist_cm: num('waist_cm'),
    total_cholesterol: num('total_cholesterol') ?? num('tc') ?? num('cholesterol'),
    ldl_cholesterol: num('ldl_cholesterol') ?? num('ldl'),
    hdl_cholesterol: num('hdl_cholesterol') ?? num('hdl'),
    triglyceride: num('triglyceride') ?? num('tg') ?? num('triglycerides'),
    fasting_glucose: num('fasting_glucose') ?? num('fpg') ?? num('glucose'),
    hba1c: num('hba1c'),
    smoke_status: smokeFromNumeric || (['never', 'former', 'current'].includes(smoke) ? smoke : 'never'),
    physical_activity: ['unknown', 'sedentary', 'light', 'moderate', 'heavy'].includes(act) ? act : 'unknown',
    diabetes: Math.max(bin('diabetes'), bin('diabetes_history')),
    hypertension_dx: Math.max(bin('hypertension_dx'), bin('hypertension'), bin('hypertension_history')),
    dyslipidemia: bin('dyslipidemia'),
    family_history_cad: Math.max(bin('family_history_cad'), bin('family_history')),
    chest_pain_symptom: bin('chest_pain_symptom')
  }
}

/** 小写列名 -> 单元格原值 */
export function buildCsvRowLookupLower (row) {
  const m = {}
  if (!row) return m
  Object.keys(row).forEach((k) => {
    m[String(k).trim().toLowerCase()] = row[k]
  })
  return m
}

export function numericFromLookup (lookup, colName) {
  const key = String(colName).trim().toLowerCase()
  const raw = lookup[key]
  if (raw === null || raw === undefined || raw === '') return 0
  const x = parseFloat(String(raw).replace(/,/g, '.'))
  return Number.isFinite(x) ? x : 0
}

/**
 * 按训练时保存的 feature_names 顺序从 CSV 行取值（列名大小写不敏感；缺列填 0）
 */
export function featureVectorFromModelColumnNames (row, featureNames) {
  if (!Array.isArray(featureNames) || featureNames.length === 0) return null
  const lookup = buildCsvRowLookupLower(row)
  return featureNames.map((name) => numericFromLookup(lookup, name))
}
