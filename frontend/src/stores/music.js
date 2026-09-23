import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import { getMusicList, uploadMusic, updateMusic, deleteMusic, batchUploadMusic } from '@/api/music'

export const useMusicStore = defineStore('music', () => {
  const base = useCrudStore('music', {
    getList: getMusicList,
    upload: uploadMusic,
    update: updateMusic,
    delete: deleteMusic,
  })

  // 批量上传：暴露独立方法，避免污染通用 CRUD
  async function batchUpload(payload) {
    return await batchUploadMusic(payload)
  }

  return { ...base, batchUpload }
})