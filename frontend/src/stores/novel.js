import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import { getNovelList, uploadNovel, updateNovel, deleteNovel } from '@/api/novel'

export const useNovelStore = defineStore('novel', () =>
  useCrudStore('novel', {
    getList: getNovelList,
    upload: uploadNovel,
    update: updateNovel,
    delete: deleteNovel
  })
)