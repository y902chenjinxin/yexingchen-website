/**
 * useCultivationStore.js
 * 修炼记录持久化 store
 * 基于 localStorage 保存用户修炼历程
 */

import { ref, computed } from 'vue'

const STORAGE_KEY = 'cultivation_chronicle'

// 单例模式
let store = null

function getStore() {
  if (!store) {
    store = createStore()
  }
  return store
}

function createStore() {
  const events = ref([])

  // 从 localStorage 加载
  function load() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const data = JSON.parse(stored)
        events.value = data.events || []
      }
    } catch {
      events.value = []
    }
  }

  // 保存到 localStorage
  function save() {
    try {
      const data = {
        events: events.value,
        updatedAt: new Date().toISOString()
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch {
      // localStorage 不可用
    }
  }

  // 添加记录
  function addRecord(type, description, metadata = {}) {
    const record = {
      id: Date.now(),
      type,
      description,
      timestamp: new Date().toISOString(),
      ...metadata
    }
    events.value.unshift(record) // 最新在前
    save()
    return record
  }

  // 获取所有记录
  function getRecords() {
    return events.value
  }

  // 清空记录
  function clearRecords() {
    events.value = []
    save()
  }

  // 初始化
  load()

  return {
    events,
    addRecord,
    getRecords,
    clearRecords
  }
}

export function useCultivationStore() {
  return getStore()
}

// 事件类型常量
export const RECORD_TYPES = {
  LOGIN: 'login',
  VISIT_ISLAND: 'visit_island',
  RANDOM_EVENT: 'random_event',
  CULTIVATION_COMPLETE: 'cultivation_complete'
}

// 事件类型对应的显示信息
export const RECORD_TYPE_INFO = {
  [RECORD_TYPES.LOGIN]: { icon: '🔑', label: '登录', color: 'var(--color-jade)' },
  [RECORD_TYPES.VISIT_ISLAND]: { icon: '🏝️', label: '探索', color: 'var(--color-music)' },
  [RECORD_TYPES.RANDOM_EVENT]: { icon: '✨', label: '天赐', color: 'var(--color-gold)' },
  [RECORD_TYPES.CULTIVATION_COMPLETE]: { icon: '🎯', label: '修为', color: 'var(--color-video)' }
}