import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getToolList, createTool, updateTool, deleteTool } from '@/api/tool'

export const useToolStore = defineStore('tool', () => {
  const list = ref([])
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const res = await getToolList()
      list.value = res.data.list
      return res
    } finally {
      loading.value = false
    }
  }

  async function add(data) {
    return await createTool(data)
  }

  async function update(id, data) {
    return await updateTool(id, data)
  }

  async function remove(id) {
    return await deleteTool(id)
  }

  return { list, loading, fetchList, add, update, remove }
})