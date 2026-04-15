/**
 * 预留受试者 ID 的本地推断（仅根据 H5 文件名）。
 * 须与 backend scripts/train_from_h5.py 中 subject_key_from_h5_path
 * 在「无元数据命中」时的文件名分支保持一致。
 */

export function inferSubjectKeyFromFilename(fileName) {
  const base = String(fileName || '').split(/[/\\]/).pop() || ''
  const stem = base.replace(/\.h5$/i, '')
  const parts = stem.split('_')
  if (parts.length >= 2 && /^\d+$/.test(parts[1])) {
    const prefix = parts[0]
    if (prefix.toLowerCase().startsWith('subject') || prefix.length > 4) {
      return stem
    }
    return parts[1]
  }
  if (parts.length >= 1 && parts[0]) {
    return parts[0]
  }
  return stem || base
}

export function parseHoldoutSubjectIds(raw) {
  if (!raw || !String(raw).trim()) return []
  const s = String(raw)
    .replace(/，/g, ',')
    .replace(/；/g, ',')
    .replace(/;/g, ',')
  return s
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
}

/**
 * @param {Array<{ name?: string }|File>} files 浏览器 File 或带 name 的对象
 * @returns {string[]} 去重、排序后的推断 ID
 */
export function suggestedHoldoutIdsFromFiles(files) {
  if (!files || !files.length) return []
  const keys = new Set()
  for (const f of files) {
    const name = f && (f.name || f.raw?.name)
    if (!name || !/\.h5$/i.test(name)) continue
    keys.add(inferSubjectKeyFromFilename(name))
  }
  return Array.from(keys).sort((a, b) =>
    a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })
  )
}
