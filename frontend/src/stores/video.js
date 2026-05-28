import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import { getVideoList, uploadVideo, updateVideo, deleteVideo } from '@/api/video'

export const useVideoStore = defineStore('video', () =>
  useCrudStore('video', {
    getList: getVideoList,
    upload: uploadVideo,
    update: updateVideo,
    delete: deleteVideo
  })
)