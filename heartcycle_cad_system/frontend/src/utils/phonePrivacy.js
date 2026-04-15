/**
 * 列表/详情展示用手机号脱敏（完整号码仍由接口返回，编辑表单中可完整填写）
 */
export function maskPhone(phone) {
  if (phone == null || phone === '') return '-'
  const s = String(phone).trim()
  if (!s) return '-'
  if (s.length <= 4) return '****'
  if (s.length >= 11) return `${s.slice(0, 3)}****${s.slice(-4)}`
  return `${s.slice(0, 2)}****${s.slice(-2)}`
}
