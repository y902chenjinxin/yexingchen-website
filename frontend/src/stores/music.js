import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import { getMusicList, uploadMusic, updateMusic, deleteMusic } from '@/api/music'

export const useMusicStore = defineStore('music', () =>
  useCrudStore('music', {
    getList: getMusicList,
    upload: uploadMusic,
    update: updateMusic,
    delete: deleteMusic
  })
)