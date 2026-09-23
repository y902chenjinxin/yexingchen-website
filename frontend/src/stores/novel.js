import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import { getNovelList, uploadNovel, updateNovel, deleteNovel, batchUploadNovel } from '@/api/novel'

export const useNovelStore = defineStore('novel', () => {
  const base = useCrudStore('novel', {
    getList: getNovelList,
    upload: uploadNovel,
    update: updateNovel,
    delete: deleteNovel,
  })

  async function batchUpload(payload) {
    return await batchUploadNovel(payload)
  }

  return { ...base, batchUpload }
})