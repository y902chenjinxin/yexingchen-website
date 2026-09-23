import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import { getVideoList, uploadVideo, updateVideo, deleteVideo, batchUploadVideo } from '@/api/video'

export const useVideoStore = defineStore('video', () => {
  const base = useCrudStore('video', {
    getList: getVideoList,
    upload: uploadVideo,
    update: updateVideo,
    delete: deleteVideo,
  })

  async function batchUpload(payload) {
    return await batchUploadVideo(payload)
  }

  return { ...base, batchUpload }
})