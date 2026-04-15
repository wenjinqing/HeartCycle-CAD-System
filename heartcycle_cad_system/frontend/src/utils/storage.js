/**
 * 本地存储工具（预测历史按登录用户隔离，避免同浏览器多账号串数据）
 */

const LEGACY_STORAGE_KEY = 'heartcycle_history'
const LEGACY_INDEX_KEY = 'heartcycle_history_index'

function _loggedInUserId() {
  try {
    const userStr = localStorage.getItem('user')
    const user = userStr ? JSON.parse(userStr) : null
    if (user && user.id != null && user.id !== '') {
      return String(user.id)
    }
  } catch {
    // ignore
  }
  return null
}

function _historyStorageKey() {
  const uid = _loggedInUserId()
  if (uid) {
    return `heartcycle_history_user_${uid}`
  }
  return LEGACY_STORAGE_KEY
}

function _historyIndexKey() {
  const uid = _loggedInUserId()
  if (uid) {
    return `heartcycle_history_index_user_${uid}`
  }
  return LEGACY_INDEX_KEY
}

export const storage = {
  // 获取下一个索引
  _getNextIndex() {
    try {
      const key = _historyIndexKey()
      const index = localStorage.getItem(key)
      const nextIndex = index ? parseInt(index, 10) + 1 : 1
      localStorage.setItem(key, nextIndex.toString())
      return nextIndex
    } catch (error) {
      console.error('获取索引失败:', error)
      return Date.now() // 如果失败，使用时间戳作为索引
    }
  },

  // 保存历史记录
  saveHistory(record) {
    try {
      const history = this.getHistory()
      const now = new Date()
      const timestamp = now.getTime()
      const dateStr = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
      
      const newRecord = {
        id: this._getNextIndex(), // 唯一索引
        timestamp: timestamp, // 时间戳（毫秒）
        date: dateStr, // 格式化日期字符串
        ...record
      }
      
      history.unshift(newRecord)
      
      // 只保留最近500条
      if (history.length > 500) {
        history.splice(500)
      }
      
      localStorage.setItem(_historyStorageKey(), JSON.stringify(history))
      return newRecord.id
    } catch (error) {
      console.error('保存历史记录失败:', error)
      return null
    }
  },

  // 获取历史记录
  getHistory() {
    try {
      const stored = localStorage.getItem(_historyStorageKey())
      const history = stored ? JSON.parse(stored) : []
      // 确保每条记录都有id和timestamp
      return history.map((record, index) => ({
        ...record,
        id: record.id || index + 1,
        timestamp: record.timestamp || new Date(record.date || Date.now()).getTime()
      }))
    } catch (error) {
      console.error('获取历史记录失败:', error)
      return []
    }
  },

  // 根据ID获取单条记录
  getHistoryById(id) {
    try {
      const history = this.getHistory()
      return history.find(record => record.id === id) || null
    } catch (error) {
      console.error('获取历史记录失败:', error)
      return null
    }
  },

  // 删除历史记录
  deleteHistory(id) {
    try {
      const history = this.getHistory()
      const index = history.findIndex(record => record.id === id)
      if (index !== -1) {
        history.splice(index, 1)
        localStorage.setItem(_historyStorageKey(), JSON.stringify(history))
        return true
      }
      return false
    } catch (error) {
      console.error('删除历史记录失败:', error)
      return false
    }
  },

  // 批量删除历史记录
  deleteHistoryBatch(ids) {
    try {
      const history = this.getHistory()
      const filtered = history.filter(record => !ids.includes(record.id))
      localStorage.setItem(_historyStorageKey(), JSON.stringify(filtered))
      return true
    } catch (error) {
      console.error('批量删除历史记录失败:', error)
      return false
    }
  },

  // 清除所有历史记录
  clearHistory() {
    try {
      localStorage.removeItem(_historyStorageKey())
      localStorage.removeItem(_historyIndexKey())
      return true
    } catch (error) {
      console.error('清除历史记录失败:', error)
      return false
    }
  },

  // 获取历史记录统计
  getHistoryStats() {
    try {
      const history = this.getHistory()
      return {
        total: history.length,
        highRisk: history.filter(r => r.prediction === 1).length,
        lowRisk: history.filter(r => r.prediction === 0).length,
        latestDate: history.length > 0 ? history[0].date : null
      }
    } catch (error) {
      console.error('获取统计信息失败:', error)
      return { total: 0, highRisk: 0, lowRisk: 0, latestDate: null }
    }
  }
}

