/**
 * 轻量 CSV 行解析：支持双引号包裹字段、字段内逗号、"" 转义
 */

export function splitCsvLine (line) {
  const result = []
  let cur = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (c === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"'
        i++
      } else {
        inQuotes = !inQuotes
      }
    } else if (c === ',' && !inQuotes) {
      result.push(cur.trim())
      cur = ''
    } else {
      cur += c
    }
  }
  result.push(cur.trim())
  return result
}

function stripCell (s) {
  let t = s
  if (t.startsWith('"') && t.endsWith('"') && t.length >= 2) {
    t = t.slice(1, -1).replace(/""/g, '"')
  }
  return t
}

/**
 * @param {string} text 整个文件内容
 * @returns {{ headers: string[], rows: Record<string, string>[] }}
 */
export function parseCsvText (text) {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  if (lines.length < 2) {
    return { headers: [], rows: [] }
  }
  const headers = splitCsvLine(lines[0]).map((h) => stripCell(h))
  const rows = lines.slice(1).map((line) => {
    const values = splitCsvLine(line).map((v) => stripCell(v))
    const row = {}
    headers.forEach((h, i) => {
      row[h] = values[i] ?? ''
    })
    return row
  })
  return { headers, rows }
}

/** 导出 CSV 单元格转义 */
export function escapeCsvField (val) {
  const s = String(val ?? '')
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}
