/**
 * 本地存储工具
 */

const STORAGE_KEY = 'heartcycle_history'
const INDEX_KEY = 'heartcycle_history_index'

export const storage = {
  // 获取下一个索引
  _getNextIndex() {
    try {
      const index = localStorage.getItem(INDEX_KEY)
      const nextIndex = index ? parseInt(index, 10) + 1 : 1
      localStorage.setItem(INDEX_KEY, nextIndex.toString())
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
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
      return newRecord.id
    } catch (error) {
      console.error('保存历史记录失败:', error)
      return null
    }
  },

  // 获取历史记录
  getHistory() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
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
        localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
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
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered))
      return true
    } catch (error) {
      console.error('批量删除历史记录失败:', error)
      return false
    }
  },

  // 清除所有历史记录
  clearHistory() {
    try {
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(INDEX_KEY)
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


