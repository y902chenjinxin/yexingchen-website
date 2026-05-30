import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getLogs } from '@/api/log'

export const useLogStore = defineStore('log', () => {
  const items = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchList(params) {
    loading.value = true
    error.value = null
    try {
      const response = await getLogs(params)
      items.value = response.data.data || response.data || []
    } catch (err) {
      error.value = err.message
      items.value = []
    } finally {
      loading.value = false
    }
  }

  return {
    items,
    loading,
    error,
    fetchList
  }
})