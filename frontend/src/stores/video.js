import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVideoList, uploadVideo, updateVideo, deleteVideo } from '@/api/video'

export const useVideoStore = defineStore('video', () => {
  const list = ref([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(20)
  const loading = ref(false)

  async function fetchList(params = {}) {
    loading.value = true
    try {
      const res = await getVideoList({ page: page.value, size: size.value, ...params })
      list.value = res.data.list
      total.value = res.data.total
      return res
    } finally {
      loading.value = false
    }
  }

  async function upload(data) {
    return await uploadVideo(data)
  }

  async function update(id, data) {
    return await updateVideo(id, data)
  }

  async function remove(id) {
    return await deleteVideo(id)
  }

  return { list, total, page, size, loading, fetchList, upload, update, remove }
})