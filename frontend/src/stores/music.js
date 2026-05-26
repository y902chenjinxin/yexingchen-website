import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMusicList, uploadMusic, updateMusic, deleteMusic } from '@/api/music'

export const useMusicStore = defineStore('music', () => {
  const list = ref([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(20)
  const loading = ref(false)

  async function fetchList(params = {}) {
    loading.value = true
    try {
      const res = await getMusicList({ page: page.value, size: size.value, ...params })
      list.value = res.data.list
      total.value = res.data.total
      return res
    } finally {
      loading.value = false
    }
  }

  async function upload(data) {
    return await uploadMusic(data)
  }

  async function update(id, data) {
    return await updateMusic(id, data)
  }

  async function remove(id) {
    return await deleteMusic(id)
  }

  return { list, total, page, size, loading, fetchList, upload, update, remove }
})