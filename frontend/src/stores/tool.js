import { defineStore } from 'pinia'
import { useCrudStore } from '@/composables/useCrudStore'
import { getToolList, createTool, updateTool, deleteTool } from '@/api/tool'

export const useToolStore = defineStore('tool', () =>
  useCrudStore('tool', {
    getList: getToolList,
    upload: createTool,
    update: updateTool,
    delete: deleteTool
  })
)