import { defineStore } from 'pinia'
import { ref } from 'vue'
import workbenchApi from '@/api/workbench'

export const useWorkbenchStore = defineStore('workbench', () => {
  const summary = ref(null)
  const loadingSummary = ref(false)

  async function loadSummary() {
    loadingSummary.value = true
    try {
      const res = await workbenchApi.summary()
      summary.value = res.data
    } finally {
      loadingSummary.value = false
    }
  }

  return { summary, loadingSummary, loadSummary }
})
